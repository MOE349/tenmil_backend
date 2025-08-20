"""
Parts & Inventory Service Layer

Production-grade CMMS parts management with FIFO inventory, transactional operations,
and comprehensive audit trail through part_movement.

Core Principles:
- FIFO (First-In, First-Out) inventory consumption
- All stock changes recorded in part_movement (immutable ledger)
- Full transaction safety with proper locking
- Idempotency support
- Data integrity with validation
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any, NamedTuple
from dataclasses import dataclass
from datetime import datetime

from django.db import transaction, models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import Part, InventoryBatch, WorkOrderPart, PartMovement
from company.models import Location
from work_orders.models import WorkOrder
from tenant_users.models import TenantUser


class InventoryError(Exception):
    """Base exception for inventory operations"""
    pass


class InsufficientStockError(InventoryError):
    """Raised when requested quantity exceeds available stock"""
    def __init__(self, part_number: str, requested: Decimal, available: Decimal):
        self.part_number = part_number
        self.requested = requested
        self.available = available
        super().__init__(f"Insufficient stock for {part_number}: requested {requested}, available {available}")


class InvalidOperationError(InventoryError):
    """Raised when operation violates business rules"""
    pass


@dataclass
class AllocationResult:
    """Result of FIFO allocation operation"""
    batch_id: str
    qty_allocated: Decimal
    unit_cost: Decimal
    total_cost: Decimal


@dataclass
class OperationResult:
    """Result of inventory operation"""
    success: bool
    allocations: List[AllocationResult]
    movements: List[str]  # Movement IDs
    work_order_parts: List[str]  # WorkOrderPart IDs (if applicable)
    message: str


class InventoryService:
    """
    Core service for parts & inventory operations
    
    Implements FIFO algorithms, transaction management, and audit trail
    """
    
    def __init__(self):
        self.User = get_user_model()
    
    def receive_parts(
        self, 
        part_id: str,
        location_id: str,
        qty: Decimal,
        unit_cost: Decimal,
        received_date: Optional[datetime] = None,
        receipt_id: Optional[str] = None,
        created_by: Optional[TenantUser] = None,
        idempotency_key: Optional[str] = None
    ) -> OperationResult:
        """
        Receive parts into inventory
        
        Creates new inventory batch and records receive movement
        
        Args:
            part_id: UUID of part to receive
            location_id: UUID of location to receive at
            qty: Quantity to receive (must be positive)
            unit_cost: Unit cost for this batch
            received_date: Date of receipt (defaults to now)
            receipt_id: External receipt reference
            created_by: User performing operation
            idempotency_key: Optional key for idempotency
            
        Returns:
            OperationResult with batch and movement details
            
        Raises:
            ValidationError: Invalid input parameters
            InvalidOperationError: Business rule violation
        """
        if qty <= 0:
            raise ValidationError("Quantity must be positive")
        if unit_cost < 0:
            raise ValidationError("Unit cost cannot be negative")
            
        received_date = received_date or timezone.now()
        
        with transaction.atomic():
            # Get part and location
            try:
                part = Part.objects.get(id=part_id)
                location = Location.objects.get(id=location_id)
            except (Part.DoesNotExist, Location.DoesNotExist) as e:
                raise InvalidOperationError(f"Invalid part or location: {e}")
            
            # Check idempotency
            if idempotency_key:
                existing_movement = PartMovement.objects.filter(
                    part=part,
                    movement_type=PartMovement.MovementType.RECEIVE,
                    receipt_id=idempotency_key
                ).first()
                if existing_movement:
                    # Return existing result
                    batch = existing_movement.inventory_batch
                    return OperationResult(
                        success=True,
                        allocations=[AllocationResult(
                            batch_id=str(batch.id),
                            qty_allocated=qty,
                            unit_cost=unit_cost,
                            total_cost=qty * unit_cost
                        )],
                        movements=[str(existing_movement.id)],
                        work_order_parts=[],
                        message=f"Received {qty} of {part.part_number} (idempotent)"
                    )
            
            # Create inventory batch
            batch = InventoryBatch.objects.create(
                part=part,
                location=location,
                qty_on_hand=qty,
                qty_reserved=Decimal('0'),
                qty_received=qty,
                last_unit_cost=unit_cost,
                received_date=received_date
            )
            
            # Create movement record
            movement = PartMovement.objects.create(
                part=part,
                inventory_batch=batch,
                to_location=location,
                movement_type=PartMovement.MovementType.RECEIVE,
                qty_delta=qty,
                receipt_id=receipt_id or idempotency_key,
                created_by=created_by
            )
            
            # Update part last price
            part.last_price = unit_cost
            part.save(update_fields=['last_price'])
            
            return OperationResult(
                success=True,
                allocations=[AllocationResult(
                    batch_id=str(batch.id),
                    qty_allocated=qty,
                    unit_cost=unit_cost,
                    total_cost=qty * unit_cost
                )],
                movements=[str(movement.id)],
                work_order_parts=[],
                message=f"Received {qty} of {part.part_number} at {location.name}"
            )
    
    def issue_to_work_order(
        self,
        work_order_id: str,
        part_id: str,
        location_id: str,
        qty_requested: Decimal,
        created_by: Optional[TenantUser] = None,
        idempotency_key: Optional[str] = None
    ) -> OperationResult:
        """
        Issue parts to work order using FIFO allocation
        
        Consumes inventory batches in FIFO order (oldest first by received_date)
        Creates work order part records and movement audit trail
        
        Args:
            work_order_id: UUID of work order
            part_id: UUID of part to issue
            location_id: UUID of location to issue from
            qty_requested: Quantity to issue
            created_by: User performing operation
            idempotency_key: Optional key for idempotency
            
        Returns:
            OperationResult with allocation details
            
        Raises:
            InsufficientStockError: Not enough inventory available
            InvalidOperationError: Business rule violation
        """
        if qty_requested <= 0:
            raise ValidationError("Quantity must be positive")
            
        with transaction.atomic():
            # Get entities
            try:
                part = Part.objects.get(id=part_id)
                location = Location.objects.get(id=location_id)
                work_order = WorkOrder.objects.get(id=work_order_id)
            except (Part.DoesNotExist, Location.DoesNotExist, WorkOrder.DoesNotExist) as e:
                raise InvalidOperationError(f"Invalid part, location, or work order: {e}")
            
            # Check idempotency
            if idempotency_key:
                existing_movements = PartMovement.objects.filter(
                    part=part,
                    work_order=work_order,
                    movement_type=PartMovement.MovementType.ISSUE,
                    receipt_id=idempotency_key
                )
                if existing_movements.exists():
                    # Return existing result
                    wo_parts = WorkOrderPart.objects.filter(
                        work_order=work_order,
                        part=part,
                        created_at__gte=existing_movements.first().created_at
                    )
                    allocations = [
                        AllocationResult(
                            batch_id=str(wp.inventory_batch.id),
                            qty_allocated=wp.qty_used,
                            unit_cost=wp.unit_cost_snapshot,
                            total_cost=wp.total_parts_cost
                        ) for wp in wo_parts
                    ]
                    return OperationResult(
                        success=True,
                        allocations=allocations,
                        movements=[str(m.id) for m in existing_movements],
                        work_order_parts=[str(wp.id) for wp in wo_parts],
                        message=f"Issued {qty_requested} of {part.part_number} (idempotent)"
                    )
            
            # Check total availability
            total_available = self._get_available_quantity(part, location)
            if total_available < qty_requested:
                raise InsufficientStockError(part.part_number, qty_requested, total_available)
            
            # Perform FIFO allocation
            allocations, movements, wo_parts = self._fifo_allocate_and_issue(
                part, location, work_order, qty_requested, created_by, idempotency_key
            )
            
            return OperationResult(
                success=True,
                allocations=allocations,
                movements=movements,
                work_order_parts=wo_parts,
                message=f"Issued {qty_requested} of {part.part_number} to WO {work_order.code}"
            )
    
    def return_from_work_order(
        self,
        work_order_id: str,
        part_id: str,
        location_id: str,
        qty_to_return: Decimal,
        created_by: Optional[TenantUser] = None,
        idempotency_key: Optional[str] = None
    ) -> OperationResult:
        """
        Return parts from work order back to inventory
        
        Returns parts to oldest available batches (FIFO return policy)
        Creates negative work order part records and return movements
        
        Args:
            work_order_id: UUID of work order
            part_id: UUID of part to return
            location_id: UUID of location to return to
            qty_to_return: Quantity to return
            created_by: User performing operation
            idempotency_key: Optional key for idempotency
            
        Returns:
            OperationResult with return details
        """
        if qty_to_return <= 0:
            raise ValidationError("Quantity must be positive")
            
        with transaction.atomic():
            # Get entities
            try:
                part = Part.objects.get(id=part_id)
                location = Location.objects.get(id=location_id)
                work_order = WorkOrder.objects.get(id=work_order_id)
            except (Part.DoesNotExist, Location.DoesNotExist, WorkOrder.DoesNotExist) as e:
                raise InvalidOperationError(f"Invalid part, location, or work order: {e}")
            
            # Check idempotency
            if idempotency_key:
                existing_movements = PartMovement.objects.filter(
                    part=part,
                    work_order=work_order,
                    movement_type=PartMovement.MovementType.RETURN,
                    receipt_id=idempotency_key
                )
                if existing_movements.exists():
                    # Return existing result
                    wo_parts = WorkOrderPart.objects.filter(
                        work_order=work_order,
                        part=part,
                        qty_used__lt=0,  # Returns are negative
                        created_at__gte=existing_movements.first().created_at
                    )
                    allocations = [
                        AllocationResult(
                            batch_id=str(wp.inventory_batch.id),
                            qty_allocated=abs(wp.qty_used),
                            unit_cost=wp.unit_cost_snapshot,
                            total_cost=abs(wp.total_parts_cost)
                        ) for wp in wo_parts
                    ]
                    return OperationResult(
                        success=True,
                        allocations=allocations,
                        movements=[str(m.id) for m in existing_movements],
                        work_order_parts=[str(wp.id) for wp in wo_parts],
                        message=f"Returned {qty_to_return} of {part.part_number} (idempotent)"
                    )
            
            # Perform FIFO return allocation
            allocations, movements, wo_parts = self._fifo_allocate_and_return(
                part, location, work_order, qty_to_return, created_by, idempotency_key
            )
            
            return OperationResult(
                success=True,
                allocations=allocations,
                movements=movements,
                work_order_parts=wo_parts,
                message=f"Returned {qty_to_return} of {part.part_number} from WO {work_order.code}"
            )
    
    def transfer_between_locations(
        self,
        part_id: str,
        from_location_id: str,
        to_location_id: str,
        qty: Decimal,
        created_by: Optional[TenantUser] = None,
        aisle: Optional[str] = None,
        row: Optional[str] = None,
        bin: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> OperationResult:
        """
        Transfer parts between locations
        
        Creates transfer_out and transfer_in movements
        Maintains cost layers at destination
        
        Args:
            part_id: UUID of part to transfer
            from_location_id: Source location UUID
            to_location_id: Destination location UUID
            qty: Quantity to transfer
            created_by: User performing operation
            idempotency_key: Optional key for idempotency
            
        Returns:
            OperationResult with transfer details
        """
        if qty <= 0:
            raise ValidationError("Quantity must be positive")
        if from_location_id == to_location_id:
            raise ValidationError("Source and destination locations must be different")
            
        with transaction.atomic():
            # Get entities
            try:
                part = Part.objects.get(id=part_id)
                from_location = Location.objects.get(id=from_location_id)
                to_location = Location.objects.get(id=to_location_id)
            except (Part.DoesNotExist, Location.DoesNotExist) as e:
                raise InvalidOperationError(f"Invalid part or location: {e}")
            
            # Check availability at source
            total_available = self._get_available_quantity(part, from_location)
            if total_available < qty:
                raise InsufficientStockError(part.part_number, qty, total_available)
            
            # Check idempotency
            if idempotency_key:
                existing_movements = PartMovement.objects.filter(
                    part=part,
                    from_location=from_location,
                    to_location=to_location,
                    movement_type__in=[PartMovement.MovementType.TRANSFER_OUT, PartMovement.MovementType.TRANSFER_IN],
                    receipt_id=idempotency_key
                )
                if existing_movements.exists():
                    # Return existing result (simplified)
                    return OperationResult(
                        success=True,
                        allocations=[],
                        movements=[str(m.id) for m in existing_movements],
                        work_order_parts=[],
                        message=f"Transferred {qty} of {part.part_number} (idempotent)"
                    )
            
            # Perform transfer
            allocations, movements = self._perform_transfer(
                part, from_location, to_location, qty, created_by, idempotency_key, aisle, row, bin
            )
            
            return OperationResult(
                success=True,
                allocations=allocations,
                movements=movements,
                work_order_parts=[],
                message=f"Transferred {qty} of {part.part_number} from {from_location.name} to {to_location.name}"
            )
    
    def get_on_hand_by_part_location(
        self, 
        part_id: Optional[str] = None,
        location_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get on-hand quantities by part and location"""
        queryset = InventoryBatch.objects.values(
            'part__id', 'part__part_number', 'part__name',
            'location__id', 'location__name'
        ).annotate(
            total_on_hand=models.Sum('qty_on_hand'),
            total_reserved=models.Sum('qty_reserved')
        ).filter(
            total_on_hand__gt=0
        )
        
        if part_id:
            queryset = queryset.filter(part__id=part_id)
        if location_id:
            queryset = queryset.filter(location__id=location_id)
            
        return list(queryset.order_by('part__part_number', 'location__name'))
    
    def get_batches(
        self,
        part_id: Optional[str] = None,
        location_id: Optional[str] = None
    ) -> List[InventoryBatch]:
        """Get inventory batches with optional filtering"""
        queryset = InventoryBatch.objects.select_related('part', 'location')
        
        if part_id:
            queryset = queryset.filter(part__id=part_id)
        if location_id:
            queryset = queryset.filter(location__id=location_id)
            
        return list(queryset.order_by('part__part_number', 'location__name', 'received_date'))
    
    def get_work_order_parts(self, work_order_id: str) -> Dict[str, Any]:
        """Get work order parts summary with total cost"""
        wo_parts = WorkOrderPart.objects.filter(
            work_order__id=work_order_id
        ).select_related('part', 'inventory_batch')
        
        total_cost = sum(wp.total_parts_cost for wp in wo_parts)
        
        return {
            'work_order_id': work_order_id,
            'parts': list(wo_parts),
            'total_parts_cost': total_cost
        }
    
    def get_movements(
        self,
        part_id: Optional[str] = None,
        location_id: Optional[str] = None,
        work_order_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[PartMovement]:
        """Get part movements with optional filtering"""
        queryset = PartMovement.objects.select_related(
            'part', 'from_location', 'to_location', 'work_order', 'inventory_batch'
        )
        
        if part_id:
            queryset = queryset.filter(part__id=part_id)
        if location_id:
            queryset = queryset.filter(
                models.Q(from_location__id=location_id) | 
                models.Q(to_location__id=location_id)
            )
        if work_order_id:
            queryset = queryset.filter(work_order__id=work_order_id)
        if from_date:
            queryset = queryset.filter(created_at__gte=from_date)
        if to_date:
            queryset = queryset.filter(created_at__lte=to_date)
            
        return list(queryset[:limit])
    
    # Private helper methods
    
    def _get_available_quantity(self, part: Part, location: Location) -> Decimal:
        """Get total available quantity for part at location"""
        return InventoryBatch.objects.filter(
            part=part,
            location=location,
            qty_on_hand__gt=0
        ).aggregate(
            total=models.Sum('qty_on_hand')
        )['total'] or Decimal('0')
    
    def _fifo_allocate_and_issue(
        self,
        part: Part,
        location: Location,
        work_order: WorkOrder,
        qty_needed: Decimal,
        created_by: Optional[TenantUser],
        idempotency_key: Optional[str]
    ) -> Tuple[List[AllocationResult], List[str], List[str]]:
        """Perform FIFO allocation and issue to work order"""
        # Get candidate batches with locking (FIFO by received_date)
        candidate_batches = InventoryBatch.objects.filter(
            part=part,
            location=location,
            qty_on_hand__gt=0
        ).select_for_update(skip_locked=True).order_by('received_date')
        
        allocations = []
        movements = []
        wo_parts = []
        remaining = qty_needed
        
        for batch in candidate_batches:
            if remaining <= 0:
                break
                
            # Determine how much to take from this batch
            take = min(remaining, batch.qty_on_hand)
            
            # Update batch quantity
            batch.qty_on_hand -= take
            batch.save(update_fields=['qty_on_hand'])
            
            # Create movement record
            movement = PartMovement.objects.create(
                part=part,
                inventory_batch=batch,
                from_location=location,
                movement_type=PartMovement.MovementType.ISSUE,
                qty_delta=-take,
                work_order=work_order,
                receipt_id=idempotency_key,
                created_by=created_by
            )
            
            # Create work order part record
            wo_part = WorkOrderPart.objects.create(
                work_order=work_order,
                part=part,
                inventory_batch=batch,
                qty_used=take,
                unit_cost_snapshot=batch.last_unit_cost
                # total_parts_cost calculated in model save()
            )
            
            # Track results
            allocations.append(AllocationResult(
                batch_id=str(batch.id),
                qty_allocated=take,
                unit_cost=batch.last_unit_cost,
                total_cost=take * batch.last_unit_cost
            ))
            movements.append(str(movement.id))
            wo_parts.append(str(wo_part.id))
            
            remaining -= take
        
        if remaining > 0:
            raise InsufficientStockError(part.part_number, qty_needed, qty_needed - remaining)
        
        return allocations, movements, wo_parts
    
    def _fifo_allocate_and_return(
        self,
        part: Part,
        location: Location,
        work_order: WorkOrder,
        qty_to_return: Decimal,
        created_by: Optional[TenantUser],
        idempotency_key: Optional[str]
    ) -> Tuple[List[AllocationResult], List[str], List[str]]:
        """Perform FIFO allocation for returns (return to oldest batches)"""
        # Get batches for return (oldest first)
        candidate_batches = InventoryBatch.objects.filter(
            part=part,
            location=location
        ).select_for_update(skip_locked=True).order_by('received_date')
        
        allocations = []
        movements = []
        wo_parts = []
        remaining = qty_to_return
        
        for batch in candidate_batches:
            if remaining <= 0:
                break
            
            # For returns, we can return any amount to any batch
            # Take all remaining or split as needed
            take = remaining  # Return full remaining to this batch
            
            # Update batch quantity
            batch.qty_on_hand += take
            batch.save(update_fields=['qty_on_hand'])
            
            # Create movement record
            movement = PartMovement.objects.create(
                part=part,
                inventory_batch=batch,
                to_location=location,
                movement_type=PartMovement.MovementType.RETURN,
                qty_delta=take,
                work_order=work_order,
                receipt_id=idempotency_key,
                created_by=created_by
            )
            
            # Create work order part record (negative for return)
            wo_part = WorkOrderPart.objects.create(
                work_order=work_order,
                part=part,
                inventory_batch=batch,
                qty_used=-take,  # Negative for return
                unit_cost_snapshot=batch.last_unit_cost
                # total_parts_cost calculated in model save()
            )
            
            # Track results
            allocations.append(AllocationResult(
                batch_id=str(batch.id),
                qty_allocated=take,
                unit_cost=batch.last_unit_cost,
                total_cost=take * batch.last_unit_cost
            ))
            movements.append(str(movement.id))
            wo_parts.append(str(wo_part.id))
            
            remaining -= take
            break  # Return all to first available batch
        
        return allocations, movements, wo_parts
    
    def _perform_transfer(
        self,
        part: Part,
        from_location: Location,
        to_location: Location,
        qty: Decimal,
        created_by: Optional[TenantUser],
        idempotency_key: Optional[str],
        aisle: Optional[str] = None,
        row: Optional[str] = None,
        bin: Optional[str] = None
    ) -> Tuple[List[AllocationResult], List[str]]:
        """Perform transfer between locations with cost preservation"""
        # Get source batches (FIFO)
        source_batches = InventoryBatch.objects.filter(
            part=part,
            location=from_location,
            qty_on_hand__gt=0
        ).select_for_update(skip_locked=True).order_by('received_date')
        
        allocations = []
        movements = []
        remaining = qty
        
        for source_batch in source_batches:
            if remaining <= 0:
                break
                
            take = min(remaining, source_batch.qty_on_hand)
            
            # Reduce source batch
            source_batch.qty_on_hand -= take
            source_batch.save(update_fields=['qty_on_hand'])
            
            # Create transfer_out movement
            out_movement = PartMovement.objects.create(
                part=part,
                inventory_batch=source_batch,
                from_location=from_location,
                movement_type=PartMovement.MovementType.TRANSFER_OUT,
                qty_delta=-take,
                receipt_id=idempotency_key,
                created_by=created_by
            )
            
            # Create or update destination batch with same cost/date
            dest_batch, created = InventoryBatch.objects.get_or_create(
                part=part,
                location=to_location,
                received_date=source_batch.received_date,
                last_unit_cost=source_batch.last_unit_cost,
                aisle=aisle,
                row=row,
                bin=bin,
                defaults={
                    'qty_on_hand': take,
                    'qty_reserved': Decimal('0'),
                    'qty_received': take
                }
            )
            
            if not created:
                # Update existing batch - only qty_on_hand should change
                dest_batch.qty_on_hand += take
                dest_batch.save(update_fields=['qty_on_hand'])
            
            # Create transfer_in movement
            in_movement = PartMovement.objects.create(
                part=part,
                inventory_batch=dest_batch,
                to_location=to_location,
                movement_type=PartMovement.MovementType.TRANSFER_IN,
                qty_delta=take,
                receipt_id=idempotency_key,
                created_by=created_by
            )
            
            # Track results
            allocations.append(AllocationResult(
                batch_id=str(dest_batch.id),
                qty_allocated=take,
                unit_cost=source_batch.last_unit_cost,
                total_cost=take * source_batch.last_unit_cost
            ))
            movements.extend([str(out_movement.id), str(in_movement.id)])
            
            remaining -= take
        
        return allocations, movements
    
    def get_part_locations_on_hand(self, part_id: str) -> List[Dict]:
        """
        Get all locations with aggregated inventory batch records for a specific part.
        Returns raw data that can be formatted differently by different endpoints.
        
        Args:
            part_id: The ID of the part to get location data for
            
        Returns:
            List of dictionaries containing location and quantity data
            
        Raises:
            InventoryError: If part is not found or invalid
        """
        from django.db.models import Sum
        
        try:
            # Verify part exists
            part = Part.objects.get(id=part_id)
        except Part.DoesNotExist:
            raise InventoryError(f"Part with ID {part_id} does not exist")
        
        # Get aggregated data grouped by location, aisle, row, and bin
        inventory_data = InventoryBatch.objects.filter(
            part=part
        ).select_related('location', 'location__site').values(
            'location__id',
            'location__name',
            'location__site__id',
            'location__site__code',
            'location__site__name',
            'aisle',
            'row',
            'bin'
        ).annotate(
            total_qty_on_hand=Sum('qty_on_hand')
        ).order_by('location__name', 'aisle', 'row', 'bin')
        
        return list(inventory_data)


# Global service instance
inventory_service = InventoryService()
