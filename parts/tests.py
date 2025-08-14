"""
Comprehensive tests for Parts & Inventory Module
Tests FIFO correctness, concurrency safety, idempotency, and all business logic.
"""

from django.test import TestCase, TransactionTestCase
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import threading
import time
import uuid
from unittest.mock import Mock

# Mock classes for testing since tenant models require tenant schema
class MockUser:
    def __init__(self, id=1, email='test@example.com', name='Test User'):
        self.id = id
        self.email = email
        self.name = name

class MockSite:
    def __init__(self, id=1, name='Test Site', code='TS001'):
        self.id = id
        self.name = name
        self.code = code

class MockLocation:
    def __init__(self, id=1, name='Test Location', slug='test-location', site=None):
        self.id = id
        self.name = name
        self.slug = slug
        self.site = site or MockSite()

class MockWorkOrder:
    def __init__(self, id=1, code='WO-001', description='Test WO'):
        self.id = id
        self.code = code
        self.description = description

class MockEquipment:
    def __init__(self, id=1, code='EQ-001', name='Test Equipment', location=None):
        self.id = id
        self.code = code
        self.name = name
        self.location = location or MockLocation()
from company.models import Site, Location
from work_orders.models import WorkOrder, WorkOrderStatusNames, MaintenanceType, Priority
from core.models import WorkOrderStatusControls, HighLevelMaintenanceType

from parts.models import Part, InventoryBatch, WorkOrderPart, PartMovement, IdempotencyKey
from parts.services import (
    InventoryService, InsufficientStockError, IdempotencyConflictError, InventoryError
)


class BaseInventoryTestCase(TestCase):
    """Base test case with common setup for inventory tests"""
    
    def setUp(self):
        """Set up test data"""
        # Create mock user for testing
        self.user = MockUser(id=1, email='test@example.com', name='Test User')
        
        # Create mock site and locations
        self.site = MockSite(id=1, name='Test Site', code='TS001')
        self.location = MockLocation(id=1, name='Warehouse A', slug='warehouse-a', site=self.site)
        self.location_b = MockLocation(id=2, name='Warehouse B', slug='warehouse-b', site=self.site)
        
        # Create test part
        self.part = Part.objects.create(
            part_number='TEST-001',
            name='Test Part',
            description='A test part for testing',
            category='Test Category',
            make='Test Manufacturer'
        )
        self.part2 = Part.objects.create(
            part_number='TEST-002',
            name='Test Part 2',
            description='Another test part',
            category='Test Category',
            make='Test Manufacturer'
        )
        
        # Create mock work order and related objects
        self.equipment = MockEquipment(id=1, code='EQ-001', name='Test Equipment', location=self.location)
        self.work_order = MockWorkOrder(id=1, code='WO-001', description='Test work order')


class InventoryReceiveTestCase(BaseInventoryTestCase):
    """Test cases for receiving parts into inventory"""
    
    def test_receive_parts_success(self):
        """Test successful parts receipt"""
        result = InventoryService.receive_parts(
            part_id=str(self.part.id),
            location_id=str(self.location.id),
            qty=100,
            unit_cost=Decimal('10.50'),
            received_date=date.today(),
            created_by=self.user,
            receipt_id='REC-001'
        )
        
        # Verify result
        self.assertEqual(result['qty_received'], 100)
        self.assertEqual(result['total_value'], Decimal('1050.00'))
        
        # Verify database records
        batch = InventoryBatch.objects.get(id=result['batch_id'])
        self.assertEqual(batch.qty_on_hand, 100)
        self.assertEqual(batch.last_unit_cost, Decimal('10.50'))
        
        movement = PartMovement.objects.get(id=result['movement_id'])
        self.assertEqual(movement.movement_type, 'receive')
        self.assertEqual(movement.qty_delta, 100)
        
        # Verify part last price updated
        self.part.refresh_from_db()
        self.assertEqual(self.part.last_price, Decimal('10.50'))
    
    def test_receive_parts_invalid_qty(self):
        """Test receiving with invalid quantity"""
        with self.assertRaises(ValidationError):
            InventoryService.receive_parts(
                part_id=str(self.part.id),
                location_id=str(self.location.id),
                qty=0,  # Invalid
                unit_cost=Decimal('10.50'),
                received_date=date.today(),
                created_by=self.user
            )
    
    def test_receive_parts_negative_cost(self):
        """Test receiving with negative unit cost"""
        with self.assertRaises(ValidationError):
            InventoryService.receive_parts(
                part_id=str(self.part.id),
                location_id=str(self.location.id),
                qty=100,
                unit_cost=Decimal('-10.50'),  # Invalid
                received_date=date.today(),
                created_by=self.user
            )
    
    def test_receive_parts_nonexistent_part(self):
        """Test receiving for nonexistent part"""
        fake_uuid = str(uuid.uuid4())
        with self.assertRaises(ValidationError):
            InventoryService.receive_parts(
                part_id=fake_uuid,
                location_id=str(self.location.id),
                qty=100,
                unit_cost=Decimal('10.50'),
                received_date=date.today(),
                created_by=self.user
            )


class InventoryIssueTestCase(BaseInventoryTestCase):
    """Test cases for issuing parts to work orders"""
    
    def setUp(self):
        """Set up test data with inventory"""
        super().setUp()
        
        # Create inventory batches for FIFO testing
        self.batch1 = InventoryBatch.objects.create(
            part=self.part,
            location=self.location,
            qty_on_hand=10,
            qty_reserved=0,
            last_unit_cost=Decimal('10.00'),
            received_date=date.today() - timedelta(days=10)  # Older
        )
        self.batch2 = InventoryBatch.objects.create(
            part=self.part,
            location=self.location,
            qty_on_hand=15,
            qty_reserved=0,
            last_unit_cost=Decimal('12.00'),
            received_date=date.today() - timedelta(days=5)   # Newer
        )
    
    def test_issue_parts_fifo_single_batch(self):
        """Test FIFO logic with single batch consumption"""
        result = InventoryService.issue_to_work_order(
            work_order_id=str(self.work_order.id),
            part_id=str(self.part.id),
            location_id=str(self.location.id),
            qty_requested=5,
            created_by=self.user
        )
        
        # Verify result
        self.assertEqual(result['total_qty_issued'], 5)
        self.assertEqual(len(result['allocations']), 1)
        self.assertEqual(result['allocations'][0]['qty_issued'], 5)
        self.assertEqual(Decimal(result['allocations'][0]['unit_cost']), Decimal('10.00'))
        
        # Verify batch quantities updated
        self.batch1.refresh_from_db()
        self.assertEqual(self.batch1.qty_on_hand, 5)  # 10 - 5
        
        self.batch2.refresh_from_db()
        self.assertEqual(self.batch2.qty_on_hand, 15)  # Unchanged
        
        # Verify movement created
        movement = PartMovement.objects.filter(
            part=self.part,
            movement_type='issue',
            work_order=self.work_order
        ).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.qty_delta, -5)
        
        # Verify work order part created
        wo_part = WorkOrderPart.objects.filter(
            work_order=self.work_order,
            part=self.part
        ).first()
        self.assertIsNotNone(wo_part)
        self.assertEqual(wo_part.qty_used, 5)
        self.assertEqual(wo_part.unit_cost_snapshot, Decimal('10.00'))
        self.assertEqual(wo_part.total_parts_cost, Decimal('50.00'))
    
    def test_issue_parts_fifo_multiple_batches(self):
        """Test FIFO logic spanning multiple batches"""
        result = InventoryService.issue_to_work_order(
            work_order_id=str(self.work_order.id),
            part_id=str(self.part.id),
            location_id=str(self.location.id),
            qty_requested=15,  # More than first batch
            created_by=self.user
        )
        
        # Verify result
        self.assertEqual(result['total_qty_issued'], 15)
        self.assertEqual(len(result['allocations']), 2)
        
        # First allocation (older batch)
        alloc1 = result['allocations'][0]
        self.assertEqual(alloc1['qty_issued'], 10)
        self.assertEqual(Decimal(alloc1['unit_cost']), Decimal('10.00'))
        
        # Second allocation (newer batch)
        alloc2 = result['allocations'][1]
        self.assertEqual(alloc2['qty_issued'], 5)
        self.assertEqual(Decimal(alloc2['unit_cost']), Decimal('12.00'))
        
        # Verify batch quantities
        self.batch1.refresh_from_db()
        self.assertEqual(self.batch1.qty_on_hand, 0)  # Fully consumed
        
        self.batch2.refresh_from_db()
        self.assertEqual(self.batch2.qty_on_hand, 10)  # 15 - 5
        
        # Verify total cost calculation
        expected_cost = (10 * Decimal('10.00')) + (5 * Decimal('12.00'))
        self.assertEqual(Decimal(result['total_cost']), expected_cost)
    
    def test_issue_parts_insufficient_stock(self):
        """Test issuing more than available stock"""
        with self.assertRaises(InsufficientStockError) as cm:
            InventoryService.issue_to_work_order(
                work_order_id=str(self.work_order.id),
                part_id=str(self.part.id),
                location_id=str(self.location.id),
                qty_requested=30,  # More than total available (25)
                created_by=self.user
            )
        
        # Verify error details
        self.assertEqual(cm.exception.available_qty, 25)
    
    def test_issue_parts_zero_stock(self):
        """Test issuing when no stock available"""
        # Remove all stock
        InventoryBatch.objects.filter(part=self.part).delete()
        
        with self.assertRaises(InsufficientStockError):
            InventoryService.issue_to_work_order(
                work_order_id=str(self.work_order.id),
                part_id=str(self.part.id),
                location_id=str(self.location.id),
                qty_requested=1,
                created_by=self.user
            )


class InventoryReturnTestCase(BaseInventoryTestCase):
    """Test cases for returning parts from work orders"""
    
    def setUp(self):
        """Set up test data with issued parts"""
        super().setUp()
        
        # Create inventory batch
        self.batch = InventoryBatch.objects.create(
            part=self.part,
            location=self.location,
            qty_on_hand=5,  # Some remaining after issue
            qty_reserved=0,
            last_unit_cost=Decimal('10.00'),
            received_date=date.today()
        )
        
        # Create existing work order part (simulating previous issue)
        self.wo_part = WorkOrderPart.objects.create(
            work_order=self.work_order,
            part=self.part,
            inventory_batch=self.batch,
            qty_used=5,
            unit_cost_snapshot=Decimal('10.00'),
            total_parts_cost=Decimal('50.00')
        )
    
    def test_return_parts_success(self):
        """Test successful parts return"""
        result = InventoryService.return_from_work_order(
            work_order_id=str(self.work_order.id),
            part_id=str(self.part.id),
            location_id=str(self.location.id),
            qty_to_return=3,
            created_by=self.user
        )
        
        # Verify result
        self.assertEqual(result['total_qty_returned'], 3)
        self.assertEqual(len(result['returns']), 1)
        
        # Verify batch quantity increased
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_on_hand, 8)  # 5 + 3
        
        # Verify movement created
        movement = PartMovement.objects.filter(
            part=self.part,
            movement_type='return',
            work_order=self.work_order
        ).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.qty_delta, 3)
        
        # Verify negative work order part created
        return_wo_part = WorkOrderPart.objects.filter(
            work_order=self.work_order,
            part=self.part,
            qty_used__lt=0  # Negative for return
        ).first()
        self.assertIsNotNone(return_wo_part)
        self.assertEqual(return_wo_part.qty_used, -3)
        self.assertEqual(return_wo_part.total_parts_cost, Decimal('-30.00'))
    
    def test_return_parts_no_existing_batch(self):
        """Test returning when no batch exists at location"""
        # Remove existing batch
        self.batch.delete()
        
        result = InventoryService.return_from_work_order(
            work_order_id=str(self.work_order.id),
            part_id=str(self.part.id),
            location_id=str(self.location.id),
            qty_to_return=2,
            created_by=self.user
        )
        
        # Should create new batch
        new_batch = InventoryBatch.objects.filter(
            part=self.part,
            location=self.location
        ).first()
        self.assertIsNotNone(new_batch)
        self.assertEqual(new_batch.qty_on_hand, 2)


class InventoryTransferTestCase(BaseInventoryTestCase):
    """Test cases for transferring parts between locations"""
    
    def setUp(self):
        """Set up test data with inventory"""
        super().setUp()
        
        # Create inventory at source location
        self.batch = InventoryBatch.objects.create(
            part=self.part,
            location=self.location,
            qty_on_hand=20,
            qty_reserved=0,
            last_unit_cost=Decimal('15.00'),
            received_date=date.today()
        )
    
    def test_transfer_parts_success(self):
        """Test successful parts transfer"""
        result = InventoryService.transfer_between_locations(
            part_id=str(self.part.id),
            from_location_id=str(self.location.id),
            to_location_id=str(self.location_b.id),
            qty=8,
            created_by=self.user
        )
        
        # Verify result
        self.assertEqual(result['total_qty_transferred'], 8)
        self.assertEqual(len(result['transfers_out']), 1)
        self.assertEqual(len(result['transfers_in']), 1)
        
        # Verify source batch quantity reduced
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_on_hand, 12)  # 20 - 8
        
        # Verify destination batch created
        dest_batch = InventoryBatch.objects.filter(
            part=self.part,
            location=self.location_b
        ).first()
        self.assertIsNotNone(dest_batch)
        self.assertEqual(dest_batch.qty_on_hand, 8)
        self.assertEqual(dest_batch.last_unit_cost, Decimal('15.00'))
        
        # Verify movements created
        transfer_out = PartMovement.objects.filter(
            part=self.part,
            movement_type='transfer_out'
        ).first()
        self.assertIsNotNone(transfer_out)
        self.assertEqual(transfer_out.qty_delta, -8)
        
        transfer_in = PartMovement.objects.filter(
            part=self.part,
            movement_type='transfer_in'
        ).first()
        self.assertIsNotNone(transfer_in)
        self.assertEqual(transfer_in.qty_delta, 8)
    
    def test_transfer_parts_same_location(self):
        """Test transfer validation for same location"""
        with self.assertRaises(ValidationError):
            InventoryService.transfer_between_locations(
                part_id=str(self.part.id),
                from_location_id=str(self.location.id),
                to_location_id=str(self.location.id),  # Same location
                qty=5,
                created_by=self.user
            )
    
    def test_transfer_parts_insufficient_stock(self):
        """Test transfer with insufficient stock"""
        with self.assertRaises(InsufficientStockError):
            InventoryService.transfer_between_locations(
                part_id=str(self.part.id),
                from_location_id=str(self.location.id),
                to_location_id=str(self.location_b.id),
                qty=25,  # More than available (20)
                created_by=self.user
            )


class IdempotencyTestCase(BaseInventoryTestCase):
    """Test cases for idempotency handling"""
    
    def test_receive_parts_idempotency(self):
        """Test receive operation idempotency"""
        idempotency_key = str(uuid.uuid4())
        
        # First call
        result1 = InventoryService.receive_parts(
            part_id=str(self.part.id),
            location_id=str(self.location.id),
            qty=10,
            unit_cost=Decimal('5.00'),
            received_date=date.today(),
            created_by=self.user,
            idempotency_key=idempotency_key
        )
        
        # Second call with same key should return cached result
        result2 = InventoryService.receive_parts(
            part_id=str(self.part.id),
            location_id=str(self.location.id),
            qty=10,
            unit_cost=Decimal('5.00'),
            received_date=date.today(),
            created_by=self.user,
            idempotency_key=idempotency_key
        )
        
        # Results should be identical
        self.assertEqual(result1['batch_id'], result2['batch_id'])
        self.assertEqual(result1['movement_id'], result2['movement_id'])
        
        # Only one batch should exist
        batches = InventoryBatch.objects.filter(part=self.part, location=self.location)
        self.assertEqual(batches.count(), 1)
        self.assertEqual(batches.first().qty_on_hand, 10)
        
        # Only one movement should exist
        movements = PartMovement.objects.filter(part=self.part, movement_type='receive')
        self.assertEqual(movements.count(), 1)
    
    def test_idempotency_conflict_different_user(self):
        """Test idempotency conflict with different user"""
        idempotency_key = str(uuid.uuid4())
        
        # Create another mock user
        user2 = MockUser(id=2, email='test2@example.com', name='Test User 2')
        
        # First call with user1
        InventoryService.receive_parts(
            part_id=str(self.part.id),
            location_id=str(self.location.id),
            qty=10,
            unit_cost=Decimal('5.00'),
            received_date=date.today(),
            created_by=self.user,
            idempotency_key=idempotency_key
        )
        
        # Second call with user2 and same key should raise error
        with self.assertRaises(IdempotencyConflictError):
            InventoryService.receive_parts(
                part_id=str(self.part.id),
                location_id=str(self.location.id),
                qty=10,
                unit_cost=Decimal('5.00'),
                received_date=date.today(),
                created_by=user2,  # Different user
                idempotency_key=idempotency_key
            )


class ConcurrencyTestCase(TransactionTestCase):
    """Test cases for concurrency handling"""
    
    def setUp(self):
        """Set up test data"""
        # Create mock user for testing
        self.user = MockUser(id=1, email='test@example.com', name='Test User')
        
        # Create mock site and location
        self.site = MockSite(id=1, name='Test Site', code='TS001')
        self.location = MockLocation(id=1, name='Warehouse A', slug='warehouse-a', site=self.site)
        
        # Create test part
        self.part = Part.objects.create(
            part_number='TEST-001',
            name='Test Part',
            description='A test part for testing'
        )
        
        # Create mock work orders and equipment
        self.equipment = MockEquipment(id=1, code='EQ-001', name='Test Equipment', location=self.location)
        self.work_order1 = MockWorkOrder(id=1, code='WO-001', description='Test work order 1')
        self.work_order2 = MockWorkOrder(id=2, code='WO-002', description='Test work order 2')
        
        # Create inventory batch
        self.batch = InventoryBatch.objects.create(
            part=self.part,
            location=self.location,
            qty_on_hand=10,
            qty_reserved=0,
            last_unit_cost=Decimal('10.00'),
            received_date=date.today()
        )
    
    def test_concurrent_issue_operations(self):
        """Test concurrent issue operations don't over-allocate"""
        results = []
        errors = []
        
        def issue_parts(work_order, qty):
            try:
                result = InventoryService.issue_to_work_order(
                    work_order_id=str(work_order.id),
                    part_id=str(self.part.id),
                    location_id=str(self.location.id),
                    qty_requested=qty,
                    created_by=self.user
                )
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start concurrent threads
        thread1 = threading.Thread(target=issue_parts, args=(self.work_order1, 6))
        thread2 = threading.Thread(target=issue_parts, args=(self.work_order2, 6))
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # One should succeed, one should fail
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], InsufficientStockError)
        
        # Verify batch quantity
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.qty_on_hand, 4)  # 10 - 6 = 4


class QueryMethodsTestCase(BaseInventoryTestCase):
    """Test cases for query/read methods"""
    
    def setUp(self):
        """Set up test data with inventory"""
        super().setUp()
        
        # Create multiple parts and batches
        self.batch1 = InventoryBatch.objects.create(
            part=self.part,
            location=self.location,
            qty_on_hand=10,
            qty_reserved=2,
            last_unit_cost=Decimal('10.00'),
            received_date=date.today()
        )
        self.batch2 = InventoryBatch.objects.create(
            part=self.part,
            location=self.location_b,
            qty_on_hand=15,
            qty_reserved=0,
            last_unit_cost=Decimal('12.00'),
            received_date=date.today()
        )
        self.batch3 = InventoryBatch.objects.create(
            part=self.part2,
            location=self.location,
            qty_on_hand=5,
            qty_reserved=1,
            last_unit_cost=Decimal('8.00'),
            received_date=date.today()
        )
    
    def test_get_on_hand_summary(self):
        """Test on-hand summary query"""
        # Get all inventory
        summary = InventoryService.get_on_hand_summary()
        self.assertEqual(len(summary), 3)
        
        # Get by part
        summary = InventoryService.get_on_hand_summary(part_id=str(self.part.id))
        self.assertEqual(len(summary), 2)
        
        # Get by location
        summary = InventoryService.get_on_hand_summary(location_id=str(self.location.id))
        self.assertEqual(len(summary), 2)
        
        # Get specific part and location
        summary = InventoryService.get_on_hand_summary(
            part_id=str(self.part.id),
            location_id=str(self.location.id)
        )
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]['total_on_hand'], 10)
        self.assertEqual(summary[0]['total_reserved'], 2)
        self.assertEqual(summary[0]['total_available'], 8)
    
    def test_get_batches(self):
        """Test batch detail query"""
        # Get all batches
        batches = InventoryService.get_batches()
        self.assertEqual(len(batches), 3)
        
        # Get by part
        batches = InventoryService.get_batches(part_id=str(self.part.id))
        self.assertEqual(len(batches), 2)
        
        # Verify batch details
        batch_detail = next(b for b in batches if b['batch_id'] == str(self.batch1.id))
        self.assertEqual(batch_detail['qty_on_hand'], 10)
        self.assertEqual(batch_detail['qty_available'], 8)
        self.assertEqual(Decimal(batch_detail['total_value']), Decimal('100.00'))
    
    def test_get_work_order_parts(self):
        """Test work order parts query"""
        # Create some work order parts
        WorkOrderPart.objects.create(
            work_order=self.work_order,
            part=self.part,
            inventory_batch=self.batch1,
            qty_used=5,
            unit_cost_snapshot=Decimal('10.00'),
            total_parts_cost=Decimal('50.00')
        )
        WorkOrderPart.objects.create(
            work_order=self.work_order,
            part=self.part2,
            inventory_batch=self.batch3,
            qty_used=2,
            unit_cost_snapshot=Decimal('8.00'),
            total_parts_cost=Decimal('16.00')
        )
        
        parts = InventoryService.get_work_order_parts(str(self.work_order.id))
        self.assertEqual(len(parts), 2)
        
        # Verify part details
        part_detail = next(p for p in parts if p['part_id'] == str(self.part.id))
        self.assertEqual(part_detail['qty_used'], 5)
        self.assertEqual(Decimal(part_detail['total_parts_cost']), Decimal('50.00'))
    
    def test_get_movements(self):
        """Test movement history query"""
        # Create some movements
        PartMovement.objects.create(
            part=self.part,
            inventory_batch=self.batch1,
            to_location=self.location,
            movement_type='receive',
            qty_delta=10,
            created_by=self.user
        )
        PartMovement.objects.create(
            part=self.part,
            inventory_batch=self.batch1,
            from_location=self.location,
            movement_type='issue',
            qty_delta=-5,
            work_order=self.work_order,
            created_by=self.user
        )
        
        # Get all movements
        movements = InventoryService.get_movements()
        self.assertEqual(len(movements), 2)
        
        # Get by part
        movements = InventoryService.get_movements(part_id=str(self.part.id))
        self.assertEqual(len(movements), 2)
        
        # Get by work order
        movements = InventoryService.get_movements(work_order_id=str(self.work_order.id))
        self.assertEqual(len(movements), 1)
        self.assertEqual(movements[0]['movement_type'], 'issue')
        self.assertEqual(movements[0]['qty_delta'], -5)


class IntegrationTestCase(BaseInventoryTestCase):
    """Integration tests for complete workflows"""
    
    def test_complete_inventory_lifecycle(self):
        """Test complete inventory lifecycle: receive → issue → return → transfer"""
        
        # 1. Receive parts
        receive_result = InventoryService.receive_parts(
            part_id=str(self.part.id),
            location_id=str(self.location.id),
            qty=100,
            unit_cost=Decimal('15.00'),
            received_date=date.today() - timedelta(days=5),
            created_by=self.user,
            receipt_id='REC-001'
        )
        
        # Verify receive
        batch = InventoryBatch.objects.get(id=receive_result['batch_id'])
        self.assertEqual(batch.qty_on_hand, 100)
        
        # 2. Issue parts to work order
        issue_result = InventoryService.issue_to_work_order(
            work_order_id=str(self.work_order.id),
            part_id=str(self.part.id),
            location_id=str(self.location.id),
            qty_requested=30,
            created_by=self.user
        )
        
        # Verify issue
        batch.refresh_from_db()
        self.assertEqual(batch.qty_on_hand, 70)
        wo_parts = WorkOrderPart.objects.filter(work_order=self.work_order)
        self.assertEqual(wo_parts.count(), 1)
        self.assertEqual(wo_parts.first().qty_used, 30)
        
        # 3. Return some parts
        return_result = InventoryService.return_from_work_order(
            work_order_id=str(self.work_order.id),
            part_id=str(self.part.id),
            location_id=str(self.location.id),
            qty_to_return=5,
            created_by=self.user
        )
        
        # Verify return
        batch.refresh_from_db()
        self.assertEqual(batch.qty_on_hand, 75)
        return_wo_parts = WorkOrderPart.objects.filter(
            work_order=self.work_order,
            qty_used__lt=0
        )
        self.assertEqual(return_wo_parts.count(), 1)
        self.assertEqual(return_wo_parts.first().qty_used, -5)
        
        # 4. Transfer parts to another location
        transfer_result = InventoryService.transfer_between_locations(
            part_id=str(self.part.id),
            from_location_id=str(self.location.id),
            to_location_id=str(self.location_b.id),
            qty=20,
            created_by=self.user
        )
        
        # Verify transfer
        batch.refresh_from_db()
        self.assertEqual(batch.qty_on_hand, 55)  # 75 - 20
        
        dest_batch = InventoryBatch.objects.filter(
            part=self.part,
            location=self.location_b
        ).first()
        self.assertIsNotNone(dest_batch)
        self.assertEqual(dest_batch.qty_on_hand, 20)
        
        # 5. Verify movement audit trail
        movements = PartMovement.objects.filter(part=self.part).order_by('created_at')
        self.assertEqual(movements.count(), 4)
        
        movement_types = [m.movement_type for m in movements]
        expected_types = ['receive', 'issue', 'return', 'transfer_out']
        self.assertEqual(movement_types[:4], expected_types)
        
        # Verify quantities balance
        total_delta = sum(m.qty_delta for m in movements)
        total_on_hand = InventoryBatch.objects.filter(part=self.part).aggregate(
            total=models.Sum('qty_on_hand')
        )['total']
        self.assertEqual(total_delta, total_on_hand)


if __name__ == '__main__':
    import django
    django.setup()
    
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['parts.tests'])
