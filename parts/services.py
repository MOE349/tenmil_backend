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
    qty_allocated: int
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
    
    def receive_parts_from_data(
        self,
        data: Dict[str, Any],
        created_by: Optional[TenantUser] = None
    ) -> OperationResult:
        """
        Receive parts using data dictionary (typically from API)
        
        This method handles data validation, type conversion, and field mapping
        from API data format to service layer parameters.
        
        Args:
            data: Dictionary containing part reception data
            created_by: User performing the operation
            
        Returns:
            OperationResult with batch and movement details
            
        Raises:
            ValidationError: Invalid or missing required fields
        """
        from decimal import Decimal, InvalidOperation
        from django.utils.dateparse import parse_datetime
        
        # Validate required fields
        required_fields = ['part', 'location', 'qty_received', 'last_unit_cost']
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Extract and convert data with proper error handling
        try:
            part_id = str(data['part'])
            location_id = str(data['location'])
            qty = int(data['qty_received'])
            unit_cost = Decimal(str(data['last_unit_cost']))
        except (ValueError, InvalidOperation, TypeError) as e:
            raise ValidationError(f"Invalid numeric field: {e}")
        
        # Handle received_date parsing
        received_date = data.get('received_date')
        if received_date:
            if isinstance(received_date, str):
                received_date = parse_datetime(received_date)
                if not received_date:
                    raise ValidationError("Invalid received_date format. Use ISO format (YYYY-MM-DDTHH:MM:SSZ)")
        
        # Extract positioning fields
        aisle = data.get('aisle')
        row = data.get('row')
        bin_val = data.get('bin')
        
        # Extract optional quantity fields
        qty_on_hand = None
        if 'qty_on_hand' in data and data['qty_on_hand'] is not None:
            try:
                qty_on_hand = int(data['qty_on_hand'])
            except (ValueError, TypeError):
                raise ValidationError("Invalid qty_on_hand value")
        
        qty_reserved = None
        if 'qty_reserved' in data and data['qty_reserved'] is not None:
            try:
                qty_reserved = int(data['qty_reserved'])
            except (ValueError, TypeError):
                raise ValidationError("Invalid qty_reserved value")
        
        # Call the main receive_parts method
        return self.receive_parts(
            part_id=part_id,
            location_id=location_id,
            qty=qty,
            unit_cost=unit_cost,
            received_date=received_date,
            receipt_id=data.get('receipt_id'),
            created_by=created_by,
            idempotency_key=data.get('idempotency_key'),
            aisle=aisle,
            row=row,
            bin=bin_val,
            qty_on_hand=qty_on_hand,
            qty_reserved=qty_reserved
        )
    
    def receive_parts(
        self, 
        part_id: str,
        location_id: str,
        qty: int,
        unit_cost: Decimal,
        received_date: Optional[datetime] = None,
        receipt_id: Optional[str] = None,
        created_by: Optional[TenantUser] = None,
        idempotency_key: Optional[str] = None,
        aisle: Optional[str] = None,
        row: Optional[str] = None,
        bin: Optional[str] = None,
        qty_on_hand: Optional[int] = None,
        qty_reserved: Optional[int] = None
    ) -> OperationResult:
        """
        Receive parts into inventory
        
        Creates new inventory batch and records adjustment movement
        Handles all InventoryBatch fields including positioning and quantity logic
        
        Args:
            part_id: UUID of part to receive
            location_id: UUID of location to receive at
            qty: Quantity received (qty_received - must be >= 0, zero creates placeholder batch)
            unit_cost: Unit cost for this batch
            received_date: Date of receipt (defaults to now)
            receipt_id: External receipt reference
            created_by: User performing operation
            idempotency_key: Optional key for idempotency
            aisle: Storage aisle location (optional)
            row: Storage row location (optional)
            bin: Storage bin location (optional)
            qty_on_hand: Available quantity (defaults to qty if not provided)
            qty_reserved: Reserved quantity (defaults to 0 if not provided)
            
        Returns:
            OperationResult with batch and movement details
            
        Raises:
            ValidationError: Invalid input parameters
            InvalidOperationError: Business rule violation
        """
        if qty < 0:
            raise ValidationError("Quantity cannot be negative")
        if unit_cost < 0:
            raise ValidationError("Unit cost cannot be negative")
            
        received_date = received_date or timezone.now()
        
        # Apply serializer logic: set qty_on_hand = qty (qty_received) if not provided
        if qty_on_hand is None:
            qty_on_hand = qty
        elif qty_on_hand == 0:  # If explicitly set to 0, use qty instead
            qty_on_hand = qty
            
        # Set qty_reserved to 0 if not provided
        if qty_reserved is None:
            qty_reserved = 0
            
        # Validate quantity relationships
        if qty_on_hand < 0:
            raise ValidationError("Quantity on hand cannot be negative")
        if qty_reserved < 0:
            raise ValidationError("Quantity reserved cannot be negative")
        if qty_on_hand > qty:
            raise ValidationError("Quantity on hand cannot exceed quantity received")
        
        with transaction.atomic():
            # Get part and location
            try:
                part = Part.objects.get(id=part_id)
                location = Location.objects.get(id=location_id)
            except (Part.DoesNotExist, Location.DoesNotExist) as e:
                raise InvalidOperationError(f"Invalid part or location: {e}")
            
            # Check idempotency
            if idempotency_key:
                # For zero quantities, look for existing batches with same key characteristics
                # since no movement is created to track by receipt_id
                if qty == 0:
                    existing_batch = InventoryBatch.objects.filter(
                        part=part,
                        location=location,
                        qty_received=0,
                        last_unit_cost=unit_cost,
                        received_date=received_date
                    ).first()
                    if existing_batch:
                        return OperationResult(
                            success=True,
                            allocations=[AllocationResult(
                                batch_id=str(existing_batch.id),
                                qty_allocated=existing_batch.qty_on_hand,
                                unit_cost=existing_batch.last_unit_cost,
                                total_cost=existing_batch.qty_on_hand * existing_batch.last_unit_cost
                            )],
                            movements=[],
                            work_order_parts=[],
                            message=f"Created placeholder batch for {part.part_number} (idempotent)"
                        )
                else:
                    # For non-zero quantities, look for existing movements as before
                    existing_movement = PartMovement.objects.filter(
                        part=part,
                        movement_type=PartMovement.MovementType.ADJUSTMENT,
                        receipt_id=idempotency_key
                    ).first()
                    if existing_movement:
                        # Return existing result
                        batch = existing_movement.inventory_batch
                        return OperationResult(
                            success=True,
                            allocations=[AllocationResult(
                                batch_id=str(batch.id),
                                qty_allocated=batch.qty_on_hand,  # Use actual batch quantity
                                unit_cost=batch.last_unit_cost,
                                total_cost=batch.qty_on_hand * batch.last_unit_cost
                            )],
                            movements=[str(existing_movement.id)],
                            work_order_parts=[],
                            message=f"Added {batch.qty_received} of {part.part_number} (idempotent)"
                        )
            
            # Create inventory batch with positioning support
            # Handle positioning fields - convert empty strings to default values
            batch_aisle = aisle if aisle and aisle.strip() else "0"
            batch_row = row if row and row.strip() else "0"
            batch_bin = bin if bin and bin.strip() else "0"
            
            batch = InventoryBatch.objects.create(
                part=part,
                location=location,
                qty_on_hand=qty_on_hand,
                qty_reserved=qty_reserved,
                qty_received=qty,  # This is the original qty parameter
                last_unit_cost=unit_cost,
                received_date=received_date,
                aisle=batch_aisle,
                row=batch_row,
                bin=batch_bin
            )
            
            # Create movement record only if qty_on_hand > 0 (skip for placeholder batches)
            movements = []
            if qty_on_hand > 0:
                movement = PartMovement.objects.create(
                    part=part,
                    inventory_batch=batch,
                    to_location=location,
                    movement_type=PartMovement.MovementType.ADJUSTMENT,
                    qty_delta=qty_on_hand,  # Movement reflects actual available quantity added
                    receipt_id=receipt_id or idempotency_key,
                    created_by=created_by
                )
                movements = [str(movement.id)]
            
            # Update part last price only if qty > 0 (don't update price for placeholder batches)
            if qty > 0:
                part.last_price = unit_cost
                part.save(update_fields=['last_price'])
            
            # Determine message based on whether this is a placeholder batch
            if qty == 0:
                message = f"Created placeholder batch for {part.part_number} at {location.name}"
            else:
                message = f"Received {qty} of {part.part_number} at {location.name} ({qty_on_hand} available)"
            
            return OperationResult(
                success=True,
                allocations=[AllocationResult(
                    batch_id=str(batch.id),
                    qty_allocated=qty_on_hand,  # Use actual available quantity
                    unit_cost=unit_cost,
                    total_cost=qty_on_hand * unit_cost
                )],
                movements=movements,
                work_order_parts=[],
                message=message
            )
    
    def issue_to_work_order(
        self,
        work_order_id: str,
        part_id: str,
        location_id: str,
        qty_requested: int,
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
        qty_to_return: int,
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
        from_aisle: Optional[str] = None,
        from_row: Optional[str] = None,
        from_bin: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> OperationResult:
        """
        Transfer parts between locations
        
        Creates transfer_out and transfer_in movements
        Maintains cost layers at destination
        FIFO applied at position level for precise inventory management
        
        Args:
            part_id: UUID of part to transfer
            from_location_id: Source location UUID  
            to_location_id: Destination location UUID
            qty: Quantity to transfer
            created_by: User performing operation
            aisle: Destination aisle (None for no specific aisle)
            row: Destination row (None for no specific row)
            bin: Destination bin (None for no specific bin)
            from_aisle: Source aisle filter for FIFO (None for any aisle)
            from_row: Source row filter for FIFO (None for any row)
            from_bin: Source bin filter for FIFO (None for any bin)
            idempotency_key: Optional key for idempotency
            
        Returns:
            OperationResult with transfer details
        """
        if qty <= 0:
            raise ValidationError("Quantity must be positive")
        # Note: Location validation is handled in serializer with position awareness
            
        with transaction.atomic():
            # Get entities
            try:
                part = Part.objects.get(id=part_id)
                from_location = Location.objects.get(id=from_location_id)
                to_location = Location.objects.get(id=to_location_id)
            except (Part.DoesNotExist, Location.DoesNotExist) as e:
                raise InvalidOperationError(f"Invalid part or location: {e}")
            
            # Check availability at source (considering source position filter if specified)
            total_available = self._get_available_quantity_at_position(
                part, from_location, from_aisle, from_row, from_bin
            )
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
            
            # Perform transfer with position-aware FIFO
            allocations, movements = self._perform_transfer(
                part, from_location, to_location, qty, created_by, idempotency_key, 
                aisle, row, bin, from_aisle, from_row, from_bin
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
        limit: int = 100,
        aisle: Optional[str] = None,
        row: Optional[str] = None,
        bin: Optional[str] = None
    ) -> List[PartMovement]:
        """Get part movements with optional filtering including inventory_batch positioning"""
        queryset = PartMovement.objects.select_related(
            'part', 'from_location', 'to_location', 'work_order', 'inventory_batch', 'inventory_batch__location'
        )
        
        if part_id:
            queryset = queryset.filter(part__id=part_id)
            
        if location_id:
            # Filter by location - check both movement locations AND inventory_batch location
            queryset = queryset.filter(
                models.Q(from_location__id=location_id) | 
                models.Q(to_location__id=location_id) |
                models.Q(inventory_batch__location__id=location_id)
            )
            
        # Filter by inventory_batch positioning fields
        if aisle is not None:
            if aisle == '' or aisle == '0':
                # Empty string or '0' should match default value '0'
                queryset = queryset.filter(
                    models.Q(inventory_batch__aisle='0') | 
                    models.Q(inventory_batch__aisle__isnull=True) |
                    models.Q(inventory_batch__aisle='')
                )
            else:
                queryset = queryset.filter(inventory_batch__aisle=aisle)
                
        if row is not None:
            if row == '' or row == '0':
                # Empty string or '0' should match default value '0'
                queryset = queryset.filter(
                    models.Q(inventory_batch__row='0') | 
                    models.Q(inventory_batch__row__isnull=True) |
                    models.Q(inventory_batch__row='')
                )
            else:
                queryset = queryset.filter(inventory_batch__row=row)
                
        if bin is not None:
            if bin == '' or bin == '0':
                # Empty string or '0' should match default value '0'
                queryset = queryset.filter(
                    models.Q(inventory_batch__bin='0') | 
                    models.Q(inventory_batch__bin__isnull=True) |
                    models.Q(inventory_batch__bin='')
                )
            else:
                queryset = queryset.filter(inventory_batch__bin=bin)
        
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
    
    def _get_available_quantity_at_position(
        self, 
        part: Part, 
        location: Location, 
        aisle: Optional[str] = None,
        row: Optional[str] = None,
        bin: Optional[str] = None
    ) -> Decimal:
        """Get total available quantity for part at specific position within location"""
        queryset = InventoryBatch.objects.filter(
            part=part,
            location=location,
            qty_on_hand__gt=0
        )
        
        # Apply position filters - None means any value, not just null
        if aisle is not None:
            if aisle == '':
                queryset = queryset.filter(aisle__isnull=True)
            else:
                queryset = queryset.filter(aisle=aisle)
        
        if row is not None:
            if row == '':
                queryset = queryset.filter(row__isnull=True)  
            else:
                queryset = queryset.filter(row=row)
        
        if bin is not None:
            if bin == '':
                queryset = queryset.filter(bin__isnull=True)
            else:
                queryset = queryset.filter(bin=bin)
        
        return queryset.aggregate(
            total=models.Sum('qty_on_hand')
        )['total'] or Decimal('0')
    
    def _fifo_allocate_and_issue(
        self,
        part: Part,
        location: Location,
        work_order: WorkOrder,
        qty_needed: int,
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
            
            # Check if we already have a WorkOrderPart record for this batch
            existing_wo_part = WorkOrderPart.objects.filter(
                work_order=work_order,
                part=part,
                inventory_batch=batch
            ).first()
            
            if existing_wo_part:
                # Merge quantities with existing record
                existing_wo_part.qty_used += take
                existing_wo_part.total_parts_cost = existing_wo_part.qty_used * existing_wo_part.unit_cost_snapshot
                existing_wo_part.save(update_fields=['qty_used', 'total_parts_cost'])
                wo_part = existing_wo_part
            else:
                # Create new work order part record
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
            
            # Cleanup: Delete empty placeholder batches
            self._cleanup_empty_placeholder_batch(batch)
            
            remaining -= take
        
        if remaining > 0:
            raise InsufficientStockError(part.part_number, qty_needed, qty_needed - remaining)
        
        return allocations, movements, wo_parts
    
    def _fifo_allocate_and_return(
        self,
        part: Part,
        location: Location,
        work_order: WorkOrder,
        qty_to_return: int,
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
            
            # Check if we already have a WorkOrderPart record for this batch
            existing_wo_part = WorkOrderPart.objects.filter(
                work_order=work_order,
                part=part,
                inventory_batch=batch
            ).first()
            
            if existing_wo_part:
                # Merge quantities with existing record (subtract for return)
                existing_wo_part.qty_used -= take
                
                if existing_wo_part.qty_used <= 0:
                    # If quantity becomes zero or negative, delete the record
                    existing_wo_part.delete()
                    wo_part = None  # Indicate record was deleted
                else:
                    # Update the existing record
                    existing_wo_part.total_parts_cost = existing_wo_part.qty_used * existing_wo_part.unit_cost_snapshot
                    existing_wo_part.save(update_fields=['qty_used', 'total_parts_cost'])
                    wo_part = existing_wo_part
            else:
                # Create new work order part record (negative for return)
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
            if wo_part is not None:  # Only add if record wasn't deleted
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
        bin: Optional[str] = None,
        from_aisle: Optional[str] = None,
        from_row: Optional[str] = None,
        from_bin: Optional[str] = None
    ) -> Tuple[List[AllocationResult], List[str]]:
        """Perform transfer between locations with cost preservation and position-based FIFO"""
        # Get source batches with position filtering for precise FIFO
        queryset = InventoryBatch.objects.filter(
            part=part,
            location=from_location,
            qty_on_hand__gt=0
        )
        
        # Apply source position filters - None means any value, not just null
        if from_aisle is not None:
            if from_aisle == '':
                queryset = queryset.filter(aisle__isnull=True)
            else:
                queryset = queryset.filter(aisle=from_aisle)
        
        if from_row is not None:
            if from_row == '':
                queryset = queryset.filter(row__isnull=True)
            else:
                queryset = queryset.filter(row=from_row)
        
        if from_bin is not None:
            if from_bin == '':
                queryset = queryset.filter(bin__isnull=True)
            else:
                queryset = queryset.filter(bin=from_bin)
        
        source_batches = queryset.select_for_update(skip_locked=True).order_by('received_date')
        
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
            # Ensure None values are used for null positions (not empty strings)
            dest_aisle = aisle if aisle not in ('', None) else None
            dest_row = row if row not in ('', None) else None 
            dest_bin = bin if bin not in ('', None) else None
            
            dest_batch, created = InventoryBatch.objects.get_or_create(
                part=part,
                location=to_location,
                received_date=source_batch.received_date,
                last_unit_cost=source_batch.last_unit_cost,
                aisle=dest_aisle,
                row=dest_row,
                bin=dest_bin,
                defaults={
                    'qty_on_hand': take,
                    'qty_reserved': 0,
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
            
            # Cleanup: Delete empty placeholder batches
            self._cleanup_empty_placeholder_batch(source_batch)
            
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
        # Normalize blank and null positions to be treated as the same value
        from django.db.models import Case, When, Value
        
        inventory_data = InventoryBatch.objects.filter(
            part=part
        ).select_related('location', 'location__site').annotate(
            # Normalize positions: convert empty strings to None for consistent grouping
            normalized_aisle=Case(
                When(aisle='', then=Value(None)),
                When(aisle__isnull=True, then=Value(None)),
                default='aisle'
            ),
            normalized_row=Case(
                When(row='', then=Value(None)),
                When(row__isnull=True, then=Value(None)),
                default='row'
            ),
            normalized_bin=Case(
                When(bin='', then=Value(None)),
                When(bin__isnull=True, then=Value(None)),
                default='bin'
            )
        ).values(
            'location__id',
            'location__name',
            'location__site__id',
            'location__site__code',
            'location__site__name',
            'normalized_aisle',
            'normalized_row',
            'normalized_bin'
        ).annotate(
            total_qty_on_hand=Sum('qty_on_hand')
        ).order_by('location__name', 'normalized_aisle', 'normalized_row', 'normalized_bin')
        
        return list(inventory_data)
    
    def _cleanup_empty_placeholder_batch(self, batch: InventoryBatch) -> bool:
        """
        Clean up empty placeholder batches that were never actually received.
        
        Args:
            batch: The batch to potentially clean up
            
        Returns:
            bool: True if batch was deleted, False otherwise
        """
        # Check if batch is empty and was never received (placeholder)
        if batch.qty_on_hand == 0 and batch.qty_received == 0:
            # Check if this is the only batch for this location/position combination
            same_position_batches = InventoryBatch.objects.filter(
                part=batch.part,
                location=batch.location,
                aisle=batch.aisle,
                row=batch.row,
                bin=batch.bin
            ).count()
            
            if same_position_batches == 1:  # Only this batch exists at this position
                batch.delete()
                return True
        
        return False
    
    def cleanup_empty_placeholder_batches(
        self, 
        part: Part, 
        location: Optional[Location] = None
    ) -> int:
        """
        Clean up all empty placeholder batches for a part (optionally at specific location).
        
        This method can be called after inventory operations to clean up any placeholder
        batches that may have been left empty.
        
        Args:
            part: The Part to clean up batches for
            location: Optional specific location to clean up (if None, cleans all locations)
            
        Returns:
            int: Number of batches deleted
        """
        # Get empty placeholder batches
        queryset = InventoryBatch.objects.filter(
            part=part,
            qty_on_hand=0,
            qty_received=0
        )
        
        if location:
            queryset = queryset.filter(location=location)
        
        deleted_count = 0
        
        # Check each empty placeholder batch
        for batch in queryset:
            if self._cleanup_empty_placeholder_batch(batch):
                deleted_count += 1
        
        return deleted_count


class LocationStringDecoder:
    """Utility class to decode formatted location strings"""
    
    @staticmethod
    def decode_location_string(location_string: str) -> Dict[str, str]:
        """
        Decode a formatted location string into its components.
        
        Input format: "SITE_CODE - LOCATION_NAME - AA1/RR2/BB3 - qty: 75.5"
        
        Returns:
            Dict containing decoded components:
            {
                'site_code': str,
                'location_name': str, 
                'aisle': str,
                'row': str,
                'bin': str,
                'qty': str
            }
        
        Raises:
            ValueError: If string format is invalid
        """
        try:
            # Split by ' - ' to get main parts
            parts = location_string.split(' - ')
            if len(parts) != 4:
                raise ValueError("Invalid format: expected 4 parts separated by ' - '")
            
            site_code = parts[0].strip()
            location_name = parts[1].strip()
            position_part = parts[2].strip()
            qty_part = parts[3].strip()
            
            # Parse position part (AA1/RR2/BB3)
            position_parts = position_part.split('/')
            if len(position_parts) != 3:
                raise ValueError("Invalid position format: expected 3 parts separated by '/'")
            
            # Extract aisle, row, bin (remove A/R/B prefixes)
            # Use None instead of empty string for null positions
            aisle_raw = position_parts[0][1:] if position_parts[0].startswith('A') else position_parts[0]
            row_raw = position_parts[1][1:] if position_parts[1].startswith('R') else position_parts[1]
            bin_raw = position_parts[2][1:] if position_parts[2].startswith('B') else position_parts[2]
            
            aisle = aisle_raw if aisle_raw else None
            row = row_raw if row_raw else None
            bin_val = bin_raw if bin_raw else None
            
            # Parse quantity (qty: 75.5)
            if not qty_part.startswith('qty: '):
                raise ValueError("Invalid quantity format: expected 'qty: <number>'")
            qty = qty_part[5:].strip()  # Remove 'qty: ' prefix
            
            return {
                'site_code': site_code,
                'location_name': location_name,
                'aisle': aisle,
                'row': row,
                'bin': bin_val,
                'qty': qty
            }
            
        except Exception as e:
            raise ValueError(f"Failed to decode location string '{location_string}': {str(e)}")
    
    @staticmethod
    def get_location_by_site_and_name(site_code: str, location_name: str):
        """
        Get Location instance by site code and location name.
        
        Returns:
            Location instance or None if not found
        """
        from company.models import Location, Site
        
        try:
            # First find the site by code
            site = Site.objects.get(code=site_code)
            # Then find the location by name within that site
            location = Location.objects.get(site=site, name=location_name)
            return location
        except (Site.DoesNotExist, Location.DoesNotExist):
            return None


# Global service instance
inventory_service = InventoryService()

# Global decoder instance
location_decoder = LocationStringDecoder()
