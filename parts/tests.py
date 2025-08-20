"""
Comprehensive tests for Parts & Inventory module

Tests cover:
- FIFO correctness
- Concurrent operations
- Return then re-issue scenarios
- Transfer operations
- Insufficient stock handling
- Idempotency
- Data integrity
- Edge cases
"""

import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import threading

from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction

from parts.models import Part, InventoryBatch, WorkOrderPart, PartMovement
from parts.services import (
    inventory_service, InsufficientStockError, InvalidOperationError
)
from company.models import CompanyProfile, Site, Location
from work_orders.models import WorkOrder, WorkOrderStatusNames, MaintenanceType, Priority
from tenant_users.models import TenantUser
from core.models import WorkOrderStatusControls, HighLevelMaintenanceType


class PartsTestCase(TestCase):
    """Base test case with common setup"""
    
    @classmethod
    def setUpTestData(cls):
        # Create test company and location
        cls.company = CompanyProfile.objects.create(
            name="Test Company",
            domain_url="test.com"
        )
        
        cls.site = Site.objects.create(
            name="Test Site",
            company=cls.company
        )
        
        cls.location1 = Location.objects.create(
            name="Location 1",
            site=cls.site
        )
        
        cls.location2 = Location.objects.create(
            name="Location 2", 
            site=cls.site
        )
        
        # Create test user
        cls.user = TenantUser.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="testpass"
        )
        
        # Create work order dependencies
        cls.status_control = WorkOrderStatusControls.objects.create(
            name="Open",
            can_create_work_order=True
        )
        
        cls.wo_status = WorkOrderStatusNames.objects.create(
            name="Open",
            control=cls.status_control
        )
        
        cls.hlm_type = HighLevelMaintenanceType.objects.create(
            name="Corrective"
        )
        
        cls.maint_type = MaintenanceType.objects.create(
            name="Repair",
            hlmtype=cls.hlm_type
        )
        
        cls.priority = Priority.objects.create(
            name="Normal"
        )
        
    def setUp(self):
        # Create test parts
        self.part1 = Part.objects.create(
            part_number="P001",
            name="Test Part 1",
            description="Test part for inventory",
            category="Test Category"
        )
        
        self.part2 = Part.objects.create(
            part_number="P002", 
            name="Test Part 2",
            description="Another test part"
        )
        
        # Create test work order
        self.work_order = WorkOrder.objects.create(
            status=self.wo_status,
            maint_type=self.maint_type,
            priority=self.priority,
            description="Test work order"
        )


class ReceivePartsTests(PartsTestCase):
    """Tests for receiving parts into inventory"""
    
    def test_receive_parts_success(self):
        """Test successful part receipt"""
        received_date = timezone.now()
        
        result = inventory_service.receive_parts(
            part_id=str(self.part1.id),
            location_id=str(self.location1.id),
            qty=Decimal('10.5'),
            unit_cost=Decimal('25.50'),
            received_date=received_date,
            receipt_id="REC001",
            created_by=self.user
        )
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.allocations), 1)
        self.assertEqual(result.allocations[0].qty_allocated, Decimal('10.5'))
        self.assertEqual(result.allocations[0].unit_cost, Decimal('25.50'))
        
        # Verify batch created
        batch = InventoryBatch.objects.get(part=self.part1, location=self.location1)
        self.assertEqual(batch.qty_on_hand, Decimal('10.5'))
        self.assertEqual(batch.last_unit_cost, Decimal('25.50'))
        
        # Verify movement created
        movement = PartMovement.objects.get(part=self.part1)
        self.assertEqual(movement.movement_type, PartMovement.MovementType.ADJUSTMENT)
        self.assertEqual(movement.qty_delta, Decimal('10.5'))
        self.assertEqual(movement.receipt_id, "REC001")
        
        # Verify part last price updated
        self.part1.refresh_from_db()
        self.assertEqual(self.part1.last_price, Decimal('25.50'))
    
    def test_receive_parts_idempotency(self):
        """Test idempotent receipt operations"""
        # First receipt
        result1 = inventory_service.receive_parts(
            part_id=str(self.part1.id),
            location_id=str(self.location1.id),
            qty=Decimal('10'),
            unit_cost=Decimal('25'),
            idempotency_key="IDEM001",
            created_by=self.user
        )
        
        # Second receipt with same idempotency key
        result2 = inventory_service.receive_parts(
            part_id=str(self.part1.id),
            location_id=str(self.location1.id),
            qty=Decimal('10'),
            unit_cost=Decimal('25'),
            idempotency_key="IDEM001",
            created_by=self.user
        )
        
        self.assertTrue(result1.success)
        self.assertTrue(result2.success)
        
        # Should only have one batch
        batches = InventoryBatch.objects.filter(part=self.part1)
        self.assertEqual(batches.count(), 1)
        self.assertEqual(batches.first().qty_on_hand, Decimal('10'))
        
        # Should only have one movement
        movements = PartMovement.objects.filter(part=self.part1)
        self.assertEqual(movements.count(), 1)
    
    def test_receive_parts_validation(self):
        """Test receipt validation errors"""
        # Negative quantity
        with self.assertRaises(ValidationError):
            inventory_service.receive_parts(
                part_id=str(self.part1.id),
                location_id=str(self.location1.id),
                qty=Decimal('-5'),
                unit_cost=Decimal('25'),
                created_by=self.user
            )
        
        # Negative unit cost
        with self.assertRaises(ValidationError):
            inventory_service.receive_parts(
                part_id=str(self.part1.id),
                location_id=str(self.location1.id),
                qty=Decimal('5'),
                unit_cost=Decimal('-25'),
                created_by=self.user
            )
        
        # Invalid part
        with self.assertRaises(InvalidOperationError):
            inventory_service.receive_parts(
                part_id=str(uuid.uuid4()),
                location_id=str(self.location1.id),
                qty=Decimal('5'),
                unit_cost=Decimal('25'),
                created_by=self.user
            )


class FIFOTests(PartsTestCase):
    """Tests for FIFO correctness in issue/return operations"""
    
    def setUp(self):
        super().setUp()
        
        # Create multiple batches with different dates and costs
        self.batch1 = InventoryBatch.objects.create(
            part=self.part1,
            location=self.location1,
            qty_on_hand=Decimal('10'),
            qty_received=Decimal('10'),
            last_unit_cost=Decimal('10.00'),
            received_date=timezone.now() - timedelta(days=3)
        )
        
        self.batch2 = InventoryBatch.objects.create(
            part=self.part1,
            location=self.location1,
            qty_on_hand=Decimal('10'),
            qty_received=Decimal('10'),
            last_unit_cost=Decimal('12.00'),
            received_date=timezone.now() - timedelta(days=2)
        )
        
        self.batch3 = InventoryBatch.objects.create(
            part=self.part1,
            location=self.location1,
            qty_on_hand=Decimal('10'),
            qty_received=Decimal('10'),
            last_unit_cost=Decimal('15.00'),
            received_date=timezone.now() - timedelta(days=1)
        )
    
    def test_fifo_issue_single_batch(self):
        """Test FIFO issue from single batch"""
        result = inventory_service.issue_to_work_order(
            work_order_id=str(self.work_order.id),
            part_id=str(self.part1.id),
            location_id=str(self.location1.id),
            qty_requested=Decimal('5'),
            created_by=self.user
        )
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.allocations), 1)
        
        # Should use oldest batch (batch1)
        allocation = result.allocations[0]
        self.assertEqual(allocation.batch_id, str(self.batch1.id))
        self.assertEqual(allocation.qty_allocated, Decimal('5'))
        self.assertEqual(allocation.unit_cost, Decimal('10.00'))
        
        # Verify batch quantity updated
        self.batch1.refresh_from_db()
        self.assertEqual(self.batch1.qty_on_hand, Decimal('5'))
    
    def test_fifo_issue_multiple_batches(self):
        """Test FIFO issue spanning multiple batches"""
        result = inventory_service.issue_to_work_order(
            work_order_id=str(self.work_order.id),
            part_id=str(self.part1.id),
            location_id=str(self.location1.id),
            qty_requested=Decimal('15'),  # More than first batch
            created_by=self.user
        )
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.allocations), 2)
        
        # Should use batches in FIFO order
        allocations = sorted(result.allocations, key=lambda x: x.unit_cost)
        
        # First allocation from batch1 (oldest, $10)
        self.assertEqual(allocations[0].qty_allocated, Decimal('10'))
        self.assertEqual(allocations[0].unit_cost, Decimal('10.00'))
        
        # Second allocation from batch2 ($12)  
        self.assertEqual(allocations[1].qty_allocated, Decimal('5'))
        self.assertEqual(allocations[1].unit_cost, Decimal('12.00'))
        
        # Verify batch quantities
        self.batch1.refresh_from_db()
        self.batch2.refresh_from_db()
        self.batch3.refresh_from_db()
        
        self.assertEqual(self.batch1.qty_on_hand, Decimal('0'))
        self.assertEqual(self.batch2.qty_on_hand, Decimal('5'))
        self.assertEqual(self.batch3.qty_on_hand, Decimal('10'))  # Untouched
        
        # Verify work order parts created
        wo_parts = WorkOrderPart.objects.filter(work_order=self.work_order)
        self.assertEqual(wo_parts.count(), 2)
        
        total_cost = sum(wp.total_parts_cost for wp in wo_parts)
        expected_cost = (Decimal('10') * Decimal('10.00')) + (Decimal('5') * Decimal('12.00'))
        self.assertEqual(total_cost, expected_cost)
    
    def test_fifo_return_to_oldest_batch(self):
        """Test FIFO return policy (return to oldest available batch)"""
        # First issue some parts
        inventory_service.issue_to_work_order(
            work_order_id=str(self.work_order.id),
            part_id=str(self.part1.id),
            location_id=str(self.location1.id),
            qty_requested=Decimal('5'),
            created_by=self.user
        )
        
        # Now return parts
        result = inventory_service.return_from_work_order(
            work_order_id=str(self.work_order.id),
            part_id=str(self.part1.id),
            location_id=str(self.location1.id),
            qty_to_return=Decimal('3'),
            created_by=self.user
        )
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.allocations), 1)
        
        # Should return to oldest batch (batch1)
        allocation = result.allocations[0]
        self.assertEqual(allocation.batch_id, str(self.batch1.id))
        self.assertEqual(allocation.qty_allocated, Decimal('3'))
        
        # Verify batch quantity updated
        self.batch1.refresh_from_db()
        self.assertEqual(self.batch1.qty_on_hand, Decimal('8'))  # 10 - 5 + 3
        
        # Verify negative work order part created
        return_wo_parts = WorkOrderPart.objects.filter(
            work_order=self.work_order,
            qty_used__lt=0
        )
        self.assertEqual(return_wo_parts.count(), 1)
        self.assertEqual(return_wo_parts.first().qty_used, Decimal('-3'))


class ConcurrencyTests(TransactionTestCase):
    """Tests for concurrent operations and locking"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test data
        cls.company = CompanyProfile.objects.create(
            name="Test Company",
            domain_url="test.com"
        )
        
        cls.site = Site.objects.create(
            name="Test Site",
            company=cls.company
        )
        
        cls.location = Location.objects.create(
            name="Test Location",
            site=cls.site
        )
        
        cls.user = TenantUser.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="testpass"
        )
        
        # Create work order dependencies
        cls.status_control = WorkOrderStatusControls.objects.create(
            name="Open",
            can_create_work_order=True
        )
        
        cls.wo_status = WorkOrderStatusNames.objects.create(
            name="Open",
            control=cls.status_control
        )
        
        cls.hlm_type = HighLevelMaintenanceType.objects.create(
            name="Corrective"
        )
        
        cls.maint_type = MaintenanceType.objects.create(
            name="Repair",
            hlmtype=cls.hlm_type
        )
        
        cls.priority = Priority.objects.create(
            name="Normal"
        )
        
        cls.part = Part.objects.create(
            part_number="CONCURRENT_TEST",
            name="Concurrent Test Part",
            description="For testing concurrent operations"
        )
        
        cls.work_order = WorkOrder.objects.create(
            status=cls.wo_status,
            maint_type=cls.maint_type,
            priority=cls.priority,
            description="Test work order"
        )
    
    def setUp(self):
        # Create fresh batch for each test
        self.batch = InventoryBatch.objects.create(
            part=self.part,
            location=self.location,
            qty_on_hand=Decimal('20'),
            qty_received=Decimal('20'),
            last_unit_cost=Decimal('10.00'),
            received_date=timezone.now()
        )
    
    def test_concurrent_issues_with_locking(self):
        """Test that concurrent issues don't exceed available stock"""
        results = []
        errors = []
        
        def issue_parts(qty):
            try:
                result = inventory_service.issue_to_work_order(
                    work_order_id=str(self.work_order.id),
                    part_id=str(self.part.id),
                    location_id=str(self.location.id),
                    qty_requested=Decimal(str(qty)),
                    created_by=self.user
                )
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Try to issue 15 parts each in 2 threads (30 total, but only 20 available)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(issue_parts, 15),
                executor.submit(issue_parts, 15)
            ]
            
            # Wait for completion
            for future in futures:
                future.result()
        
        # One should succeed, one should fail
        successful_results = [r for r in results if r.success]
        insufficient_stock_errors = [e for e in errors if isinstance(e, InsufficientStockError)]
        
        # Should have exactly one success and one failure
        self.assertEqual(len(successful_results), 1)
        self.assertEqual(len(insufficient_stock_errors), 1)
        
        # Verify total issued doesn't exceed available
        self.batch.refresh_from_db()
        self.assertGreaterEqual(self.batch.qty_on_hand, Decimal('0'))
        
        # Verify movements don't exceed original quantity
        total_issued = sum(
            abs(m.qty_delta) for m in PartMovement.objects.filter(
                part=self.part,
                movement_type=PartMovement.MovementType.ISSUE
            )
        )
        self.assertLessEqual(total_issued, Decimal('20'))


class TransferTests(PartsTestCase):
    """Tests for transfer operations between locations"""
    
    def setUp(self):
        super().setUp()
        
        # Create batch at source location
        self.source_batch = InventoryBatch.objects.create(
            part=self.part1,
            location=self.location1,
            qty_on_hand=Decimal('20'),
            qty_received=Decimal('20'),
            last_unit_cost=Decimal('15.00'),
            received_date=timezone.now() - timedelta(days=1)
        )
    
    def test_transfer_between_locations(self):
        """Test successful transfer between locations"""
        result = inventory_service.transfer_between_locations(
            part_id=str(self.part1.id),
            from_location_id=str(self.location1.id),
            to_location_id=str(self.location2.id),
            qty=Decimal('8'),
            created_by=self.user
        )
        
        self.assertTrue(result.success)
        self.assertEqual(len(result.allocations), 1)
        self.assertEqual(result.allocations[0].qty_allocated, Decimal('8'))
        
        # Verify source batch reduced
        self.source_batch.refresh_from_db()
        self.assertEqual(self.source_batch.qty_on_hand, Decimal('12'))
        
        # Verify destination batch created
        dest_batch = InventoryBatch.objects.get(
            part=self.part1,
            location=self.location2
        )
        self.assertEqual(dest_batch.qty_on_hand, Decimal('8'))
        self.assertEqual(dest_batch.last_unit_cost, Decimal('15.00'))  # Cost preserved
        
        # Verify movements created
        movements = PartMovement.objects.filter(part=self.part1)
        transfer_out = movements.filter(movement_type=PartMovement.MovementType.TRANSFER_OUT)
        transfer_in = movements.filter(movement_type=PartMovement.MovementType.TRANSFER_IN)
        
        self.assertEqual(transfer_out.count(), 1)
        self.assertEqual(transfer_in.count(), 1)
        self.assertEqual(transfer_out.first().qty_delta, Decimal('-8'))
        self.assertEqual(transfer_in.first().qty_delta, Decimal('8'))
    
    def test_transfer_insufficient_stock(self):
        """Test transfer with insufficient stock"""
        with self.assertRaises(InsufficientStockError) as cm:
            inventory_service.transfer_between_locations(
                part_id=str(self.part1.id),
                from_location_id=str(self.location1.id),
                to_location_id=str(self.location2.id),
                qty=Decimal('25'),  # More than available
                created_by=self.user
            )
        
        self.assertEqual(cm.exception.requested, Decimal('25'))
        self.assertEqual(cm.exception.available, Decimal('20'))
    
    def test_transfer_same_location_error(self):
        """Test transfer validation for same source/destination"""
        with self.assertRaises(ValidationError):
            inventory_service.transfer_between_locations(
                part_id=str(self.part1.id),
                from_location_id=str(self.location1.id),
                to_location_id=str(self.location1.id),  # Same as source
                qty=Decimal('5'),
                created_by=self.user
            )


class ReturnAndReissueTests(PartsTestCase):
    """Tests for return then re-issue scenarios"""
    
    def setUp(self):
        super().setUp()
        
        # Create batch
        self.batch = InventoryBatch.objects.create(
            part=self.part1,
            location=self.location1,
            qty_on_hand=Decimal('20'),
            qty_received=Decimal('20'),
            last_unit_cost=Decimal('10.00'),
            received_date=timezone.now()
        )
    
    def test_return_then_reissue_reconciliation(self):
        """Test that return then re-issue maintains proper reconciliation"""
        # Initial issue
        issue_result = inventory_service.issue_to_work_order(
            work_order_id=str(self.work_order.id),
            part_id=str(self.part1.id),
            location_id=str(self.location1.id),
            qty_requested=Decimal('10'),
            created_by=self.user
        )
        self.assertTrue(issue_result.success)
        
        # Verify batch state after issue
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_on_hand, Decimal('10'))
        
        # Return some parts
        return_result = inventory_service.return_from_work_order(
            work_order_id=str(self.work_order.id),
            part_id=str(self.part1.id),
            location_id=str(self.location1.id),
            qty_to_return=Decimal('3'),
            created_by=self.user
        )
        self.assertTrue(return_result.success)
        
        # Verify batch state after return
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_on_hand, Decimal('13'))  # 20 - 10 + 3
        
        # Re-issue parts
        reissue_result = inventory_service.issue_to_work_order(
            work_order_id=str(self.work_order.id),
            part_id=str(self.part1.id),
            location_id=str(self.location1.id),
            qty_requested=Decimal('2'),
            created_by=self.user
        )
        self.assertTrue(reissue_result.success)
        
        # Final verification
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_on_hand, Decimal('11'))  # 13 - 2
        
        # Verify movement history shows all operations
        movements = PartMovement.objects.filter(part=self.part1).order_by('created_at')
        self.assertEqual(movements.count(), 3)
        
        movement_types = [m.movement_type for m in movements]
        expected_types = [
            PartMovement.MovementType.ISSUE,
            PartMovement.MovementType.RETURN,
            PartMovement.MovementType.ISSUE
        ]
        self.assertEqual(movement_types, expected_types)
        
        movement_deltas = [m.qty_delta for m in movements]
        expected_deltas = [Decimal('-10'), Decimal('3'), Decimal('-2')]
        self.assertEqual(movement_deltas, expected_deltas)
        
        # Verify work order parts reconciliation
        wo_parts = WorkOrderPart.objects.filter(work_order=self.work_order)
        total_qty_used = sum(wp.qty_used for wp in wo_parts)
        self.assertEqual(total_qty_used, Decimal('9'))  # 10 - 3 + 2


class InsufficientStockTests(PartsTestCase):
    """Tests for insufficient stock scenarios"""
    
    def test_insufficient_stock_atomic_failure(self):
        """Test that insufficient stock fails atomically with no partial writes"""
        # Create small batch
        InventoryBatch.objects.create(
            part=self.part1,
            location=self.location1,
            qty_on_hand=Decimal('5'),
            qty_received=Decimal('5'),
            last_unit_cost=Decimal('10.00'),
            received_date=timezone.now()
        )
        
        # Count initial records
        initial_movements = PartMovement.objects.count()
        initial_wo_parts = WorkOrderPart.objects.count()
        
        # Try to issue more than available
        with self.assertRaises(InsufficientStockError):
            inventory_service.issue_to_work_order(
                work_order_id=str(self.work_order.id),
                part_id=str(self.part1.id),
                location_id=str(self.location1.id),
                qty_requested=Decimal('10'),  # More than available
                created_by=self.user
            )
        
        # Verify no partial records created
        self.assertEqual(PartMovement.objects.count(), initial_movements)
        self.assertEqual(WorkOrderPart.objects.count(), initial_wo_parts)
        
        # Verify batch unchanged
        batch = InventoryBatch.objects.get(part=self.part1, location=self.location1)
        self.assertEqual(batch.qty_on_hand, Decimal('5'))


class IdempotencyTests(PartsTestCase):
    """Tests for idempotency behavior"""
    
    def setUp(self):
        super().setUp()
        
        # Create batch for testing
        self.batch = InventoryBatch.objects.create(
            part=self.part1,
            location=self.location1,
            qty_on_hand=Decimal('20'),
            qty_received=Decimal('20'),
            last_unit_cost=Decimal('10.00'),
            received_date=timezone.now()
        )
    
    def test_idempotent_issue_operation(self):
        """Test that re-posting same issue request returns original result"""
        idempotency_key = "ISSUE_001"
        
        # First request
        result1 = inventory_service.issue_to_work_order(
            work_order_id=str(self.work_order.id),
            part_id=str(self.part1.id),
            location_id=str(self.location1.id),
            qty_requested=Decimal('5'),
            created_by=self.user,
            idempotency_key=idempotency_key
        )
        
        # Second request with same key
        result2 = inventory_service.issue_to_work_order(
            work_order_id=str(self.work_order.id),
            part_id=str(self.part1.id),
            location_id=str(self.location1.id),
            qty_requested=Decimal('5'),
            created_by=self.user,
            idempotency_key=idempotency_key
        )
        
        # Both should succeed
        self.assertTrue(result1.success)
        self.assertTrue(result2.success)
        
        # Should have same allocations
        self.assertEqual(len(result1.allocations), len(result2.allocations))
        self.assertEqual(result1.allocations[0].qty_allocated, result2.allocations[0].qty_allocated)
        
        # Should only have deducted quantity once
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_on_hand, Decimal('15'))  # 20 - 5, not 20 - 10
        
        # Should only have one set of records
        movements = PartMovement.objects.filter(
            part=self.part1,
            work_order=self.work_order,
            movement_type=PartMovement.MovementType.ISSUE
        )
        self.assertEqual(movements.count(), 1)
        
        wo_parts = WorkOrderPart.objects.filter(work_order=self.work_order, part=self.part1)
        self.assertEqual(wo_parts.count(), 1)


class ModelValidationTests(PartsTestCase):
    """Tests for model validation and constraints"""
    
    def test_part_validation(self):
        """Test Part model validation"""
        # Duplicate part number should fail
        with self.assertRaises(Exception):  # IntegrityError
            Part.objects.create(
                part_number="P001",  # Same as existing
                name="Duplicate Part"
            )
    
    def test_inventory_batch_validation(self):
        """Test InventoryBatch model validation"""
        batch = InventoryBatch(
            part=self.part1,
            location=self.location1,
            qty_on_hand=Decimal('-5'),  # Invalid
            qty_received=Decimal('10'),
            last_unit_cost=Decimal('10.00'),
            received_date=timezone.now()
        )
        
        with self.assertRaises(ValidationError):
            batch.clean()
    
    def test_work_order_part_calculation(self):
        """Test WorkOrderPart total cost calculation"""
        batch = InventoryBatch.objects.create(
            part=self.part1,
            location=self.location1,
            qty_on_hand=Decimal('10'),
            qty_received=Decimal('10'),
            last_unit_cost=Decimal('15.50'),
            received_date=timezone.now()
        )
        
        wo_part = WorkOrderPart.objects.create(
            work_order=self.work_order,
            part=self.part1,
            inventory_batch=batch,
            qty_used=Decimal('3'),
            unit_cost_snapshot=Decimal('15.50')
        )
        
        # total_parts_cost should be auto-calculated
        expected_total = Decimal('3') * Decimal('15.50')
        self.assertEqual(wo_part.total_parts_cost, expected_total)
    
    def test_part_movement_validation(self):
        """Test PartMovement model validation"""
        # Test movement type vs qty_delta consistency
        movement = PartMovement(
            part=self.part1,
            movement_type=PartMovement.MovementType.RECEIVE,
            qty_delta=Decimal('-5'),  # Should be positive for receive
            to_location=self.location1,
            created_by=self.user
        )
        
        with self.assertRaises(ValidationError):
            movement.clean()


class ServiceQueryTests(PartsTestCase):
    """Tests for service query methods"""
    
    def setUp(self):
        super().setUp()
        
        # Create test data
        InventoryBatch.objects.create(
            part=self.part1,
            location=self.location1,
            qty_on_hand=Decimal('15'),
            qty_received=Decimal('20'),
            last_unit_cost=Decimal('10.00'),
            received_date=timezone.now()
        )
        
        InventoryBatch.objects.create(
            part=self.part1,
            location=self.location2,
            qty_on_hand=Decimal('8'),
            qty_received=Decimal('10'),
            last_unit_cost=Decimal('12.00'),
            received_date=timezone.now()
        )
        
        InventoryBatch.objects.create(
            part=self.part2,
            location=self.location1,
            qty_on_hand=Decimal('5'),
            qty_received=Decimal('5'),
            last_unit_cost=Decimal('25.00'),
            received_date=timezone.now()
        )
    
    def test_get_on_hand_by_part_location(self):
        """Test on-hand quantity queries"""
        # All parts, all locations
        all_data = inventory_service.get_on_hand_by_part_location()
        self.assertEqual(len(all_data), 3)  # 3 part-location combinations
        
        # Specific part, all locations
        part1_data = inventory_service.get_on_hand_by_part_location(part_id=str(self.part1.id))
        self.assertEqual(len(part1_data), 2)  # part1 in 2 locations
        
        total_part1_qty = sum(item['total_on_hand'] for item in part1_data)
        self.assertEqual(total_part1_qty, Decimal('23'))  # 15 + 8
        
        # Specific location, all parts
        location1_data = inventory_service.get_on_hand_by_part_location(location_id=str(self.location1.id))
        self.assertEqual(len(location1_data), 2)  # 2 parts in location1
    
    def test_get_batches(self):
        """Test batch queries"""
        # All batches
        all_batches = inventory_service.get_batches()
        self.assertEqual(len(all_batches), 3)
        
        # Batches for specific part
        part1_batches = inventory_service.get_batches(part_id=str(self.part1.id))
        self.assertEqual(len(part1_batches), 2)
        
        # Batches for specific location
        location1_batches = inventory_service.get_batches(location_id=str(self.location1.id))
        self.assertEqual(len(location1_batches), 2)
    
    def test_get_movements_filtering(self):
        """Test movement history filtering"""
        # Create some movements
        inventory_service.issue_to_work_order(
            work_order_id=str(self.work_order.id),
            part_id=str(self.part1.id),
            location_id=str(self.location1.id),
            qty_requested=Decimal('5'),
            created_by=self.user
        )
        
        # Test filtering
        all_movements = inventory_service.get_movements()
        self.assertGreater(len(all_movements), 0)
        
        part_movements = inventory_service.get_movements(part_id=str(self.part1.id))
        self.assertGreater(len(part_movements), 0)
        
        wo_movements = inventory_service.get_movements(work_order_id=str(self.work_order.id))
        self.assertGreater(len(wo_movements), 0)
    
    def test_get_work_order_parts_summary(self):
        """Test work order parts summary"""
        # Issue some parts to work order
        inventory_service.issue_to_work_order(
            work_order_id=str(self.work_order.id),
            part_id=str(self.part1.id),
            location_id=str(self.location1.id),
            qty_requested=Decimal('5'),
            created_by=self.user
        )
        
        summary = inventory_service.get_work_order_parts(str(self.work_order.id))
        
        self.assertEqual(summary['work_order_id'], str(self.work_order.id))
        self.assertGreater(len(summary['parts']), 0)
        self.assertGreater(summary['total_parts_cost'], Decimal('0'))


if __name__ == '__main__':
    import django
    django.setup()
    
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["parts.tests"])
