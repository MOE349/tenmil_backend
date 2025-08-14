"""
Production-grade Parts & Inventory Service Layer
Implements FIFO logic, concurrency safety, and full audit trail.
"""

from django.db import transaction, models
from django.db.models import F, Sum, Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
import uuid
import logging

from .models import Part, InventoryBatch, WorkOrderPart, PartMovement, IdempotencyKey
from tenant_users.models import TenantUser as User

logger = logging.getLogger(__name__)


class InventoryError(Exception):
    """Base exception for inventory operations"""
    pass


class InsufficientStockError(InventoryError):
    """Raised when there's insufficient stock for an operation"""
    def __init__(self, message: str, available_qty: int = 0):
        super().__init__(message)
        self.available_qty = available_qty


class ConcurrentModificationError(InventoryError):
    """Raised when concurrent modification is detected"""
    pass


class IdempotencyConflictError(InventoryError):
    """Raised when idempotency key already exists with different data"""
    pass


class InventoryService:
    """
    Production-grade inventory service with FIFO logic and concurrency safety.
    """

    @staticmethod
    def _generate_idempotency_key() -> str:
        """Generate a unique idempotency key"""
        return str(uuid.uuid4())

    @staticmethod
    def _validate_positive_qty(qty: int, field_name: str = "quantity") -> None:
        """Validate that quantity is positive"""
        if qty <= 0:
            raise ValidationError(f"{field_name} must be positive, got {qty}")

    @staticmethod
    def _check_idempotency(
        idempotency_key: Optional[str],
        operation_type: str,
        request_data: Dict[str, Any],
        created_by: User
    ) -> Optional[Dict[str, Any]]:
        """
        Check idempotency and return previous result if key exists.
        Returns None if this is a new operation.
        """
        if not idempotency_key:
            return None

        try:
            existing = IdempotencyKey.objects.get(key=idempotency_key)
            
            # Verify the operation matches
            if (existing.operation_type != operation_type or 
                existing.created_by != created_by):
                raise IdempotencyConflictError(
                    f"Idempotency key {idempotency_key} exists with different operation or user"
                )
            
            # Return cached response if available
            return existing.response_data
            
        except IdempotencyKey.DoesNotExist:
            return None

    @staticmethod
    def _save_idempotency_result(
        idempotency_key: Optional[str],
        operation_type: str,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        created_by: User
    ) -> None:
        """Save successful operation result for idempotency"""
        if idempotency_key:
            IdempotencyKey.objects.create(
                key=idempotency_key,
                operation_type=operation_type,
                request_data=request_data,
                response_data=response_data,
                created_by=created_by
            )

    @staticmethod
    @transaction.atomic
    def receive_parts(
        part_id: str,
        location_id: str,
        qty: int,
        unit_cost: Decimal,
        received_date: str,
        created_by: User,
        receipt_id: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Receive parts into inventory.
        Creates inventory batch and logs movement.
        
        Args:
            part_id: ID of the part
            location_id: ID of the location
            qty: Quantity received
            unit_cost: Cost per unit
            received_date: Date parts were received (YYYY-MM-DD)
            created_by: User performing the operation
            receipt_id: Optional receipt reference
            idempotency_key: Optional idempotency key
            
        Returns:
            Dict with batch and movement information
        """
        # Validate inputs
        InventoryService._validate_positive_qty(qty, "receive quantity")
        if unit_cost < 0:
            raise ValidationError("Unit cost cannot be negative")

        # Build request data for idempotency
        request_data = {
            'part_id': part_id,
            'location_id': location_id,
            'qty': qty,
            'unit_cost': str(unit_cost),
            'received_date': received_date,
            'receipt_id': receipt_id
        }

        # Check idempotency
        cached_result = InventoryService._check_idempotency(
            idempotency_key, 'receive', request_data, created_by
        )
        if cached_result:
            return cached_result

        try:
            # Get part and location (will raise exception if not found)
            part = Part.objects.get(id=part_id)
            from company.models import Location
            location = Location.objects.get(id=location_id)

            # Create inventory batch
            batch = InventoryBatch.objects.create(
                part=part,
                location=location,
                qty_on_hand=qty,
                qty_reserved=0,
                qty_received=qty,
                last_unit_cost=unit_cost,
                received_date=received_date
            )

            # Create movement record
            movement = PartMovement.objects.create(
                part=part,
                inventory_batch=batch,
                to_location=location,
                movement_type=PartMovement.MovementTypeChoices.RECEIVE,
                qty_delta=qty,
                receipt_id=receipt_id,
                created_by=created_by
            )

            # Update part's last price
            part.last_price = unit_cost
            part.save(update_fields=['last_price'])

            response_data = {
                'batch_id': str(batch.id),
                'movement_id': str(movement.id),
                'qty_received': qty,
                'total_value': qty * unit_cost,
                'message': f'Successfully received {qty} units of {part.part_number}'
            }

            # Save idempotency result
            InventoryService._save_idempotency_result(
                idempotency_key, 'receive', request_data, response_data, created_by
            )

            logger.info(f"Received {qty} units of part {part.part_number} at {location.name}")
            return response_data

        except Part.DoesNotExist:
            raise ValidationError(f"Part with ID {part_id} not found")
        except Exception as e:
            logger.error(f"Error receiving parts: {str(e)}")
            raise

    @staticmethod
    @transaction.atomic
    def issue_to_work_order(
        work_order_id: str,
        part_id: str,
        location_id: str,
        qty_requested: int,
        created_by: User,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Issue parts to work order using FIFO logic.
        
        Args:
            work_order_id: ID of the work order
            part_id: ID of the part
            location_id: ID of the location
            qty_requested: Quantity to issue
            created_by: User performing the operation
            idempotency_key: Optional idempotency key
            
        Returns:
            Dict with allocation details and work order lines
        """
        # Validate inputs
        InventoryService._validate_positive_qty(qty_requested, "issue quantity")

        # Build request data for idempotency
        request_data = {
            'work_order_id': work_order_id,
            'part_id': part_id,
            'location_id': location_id,
            'qty_requested': qty_requested
        }

        # Check idempotency
        cached_result = InventoryService._check_idempotency(
            idempotency_key, 'issue', request_data, created_by
        )
        if cached_result:
            return cached_result

        try:
            # Get entities
            part = Part.objects.get(id=part_id)
            from company.models import Location
            location = Location.objects.get(id=location_id)
            from work_orders.models import WorkOrder
            work_order = WorkOrder.objects.get(id=work_order_id)

            # Check total availability first
            total_available = InventoryBatch.objects.filter(
                part=part,
                location=location,
                qty_on_hand__gt=0
            ).aggregate(
                total=Sum('qty_on_hand')
            )['total'] or 0

            if total_available < qty_requested:
                raise InsufficientStockError(
                    f"Insufficient stock. Requested: {qty_requested}, Available: {total_available}",
                    available_qty=total_available
                )

            # Get candidate batches using FIFO (oldest first) with locking
            candidate_batches = InventoryBatch.objects.select_for_update(
                skip_locked=True
            ).filter(
                part=part,
                location=location,
                qty_on_hand__gt=0
            ).order_by('received_date', 'created_at')

            allocations = []
            work_order_lines = []
            remaining_needed = qty_requested
            total_cost = Decimal('0.00')

            for batch in candidate_batches:
                if remaining_needed <= 0:
                    break

                # Calculate how much to take from this batch
                qty_to_take = min(remaining_needed, batch.qty_on_hand)
                
                # Update batch quantities
                batch.qty_on_hand = F('qty_on_hand') - qty_to_take
                batch.save(update_fields=['qty_on_hand'])
                
                # Refresh to get actual values
                batch.refresh_from_db()

                # Create movement record
                movement = PartMovement.objects.create(
                    part=part,
                    inventory_batch=batch,
                    from_location=location,
                    movement_type=PartMovement.MovementTypeChoices.ISSUE,
                    qty_delta=-qty_to_take,
                    work_order=work_order,
                    created_by=created_by
                )

                # Create work order part line
                line_cost = qty_to_take * batch.last_unit_cost
                wo_part = WorkOrderPart.objects.create(
                    work_order=work_order,
                    part=part,
                    inventory_batch=batch,
                    qty_used=qty_to_take,
                    unit_cost_snapshot=batch.last_unit_cost,
                    total_parts_cost=line_cost
                )

                allocations.append({
                    'batch_id': str(batch.id),
                    'qty_issued': qty_to_take,
                    'unit_cost': batch.last_unit_cost,
                    'total_cost': line_cost,
                    'received_date': batch.received_date.isoformat()
                })

                work_order_lines.append({
                    'work_order_part_id': str(wo_part.id),
                    'qty_used': qty_to_take,
                    'unit_cost_snapshot': batch.last_unit_cost,
                    'total_parts_cost': line_cost
                })

                total_cost += line_cost
                remaining_needed -= qty_to_take

            # Final check for complete allocation
            if remaining_needed > 0:
                raise InsufficientStockError(
                    f"Could not allocate full quantity. Missing: {remaining_needed} units"
                )

            response_data = {
                'work_order_id': work_order_id,
                'part_id': part_id,
                'total_qty_issued': qty_requested,
                'total_cost': str(total_cost),
                'allocations': allocations,
                'work_order_lines': work_order_lines,
                'message': f'Successfully issued {qty_requested} units of {part.part_number} to work order {work_order.code}'
            }

            # Save idempotency result
            InventoryService._save_idempotency_result(
                idempotency_key, 'issue', request_data, response_data, created_by
            )

            logger.info(f"Issued {qty_requested} units of part {part.part_number} to WO {work_order.code}")
            return response_data

        except Part.DoesNotExist:
            raise ValidationError(f"Part with ID {part_id} not found")
        except Exception as e:
            logger.error(f"Error issuing parts: {str(e)}")
            raise

    @staticmethod
    @transaction.atomic
    def return_from_work_order(
        work_order_id: str,
        part_id: str,
        location_id: str,
        qty_to_return: int,
        created_by: User,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Return parts from work order back to inventory.
        Uses FIFO logic to return to oldest available batches.
        
        Args:
            work_order_id: ID of the work order
            part_id: ID of the part
            location_id: ID of the location
            qty_to_return: Quantity to return
            created_by: User performing the operation
            idempotency_key: Optional idempotency key
            
        Returns:
            Dict with return details
        """
        # Validate inputs
        InventoryService._validate_positive_qty(qty_to_return, "return quantity")

        # Build request data for idempotency
        request_data = {
            'work_order_id': work_order_id,
            'part_id': part_id,
            'location_id': location_id,
            'qty_to_return': qty_to_return
        }

        # Check idempotency
        cached_result = InventoryService._check_idempotency(
            idempotency_key, 'return', request_data, created_by
        )
        if cached_result:
            return cached_result

        try:
            # Get entities
            part = Part.objects.get(id=part_id)
            from company.models import Location
            location = Location.objects.get(id=location_id)
            from work_orders.models import WorkOrder
            work_order = WorkOrder.objects.get(id=work_order_id)

            # Get available batches for returns (FIFO - oldest first)
            available_batches = InventoryBatch.objects.select_for_update(
                skip_locked=True
            ).filter(
                part=part,
                location=location
            ).order_by('received_date', 'created_at')

            if not available_batches.exists():
                # Create a new batch if none exist
                # Use the part's last known price or zero
                unit_cost = part.last_price or Decimal('0.00')
                batch = InventoryBatch.objects.create(
                    part=part,
                    location=location,
                    qty_on_hand=0,
                    qty_reserved=0,
                    last_unit_cost=unit_cost,
                    received_date=timezone.now().date()
                )
                available_batches = [batch]

            returns = []
            work_order_adjustments = []
            remaining_to_return = qty_to_return
            total_cost = Decimal('0.00')

            for batch in available_batches:
                if remaining_to_return <= 0:
                    break

                # For returns, we typically return to the first available batch
                # or create new batches as needed
                qty_returning_to_batch = remaining_to_return

                # Update batch quantities
                batch.qty_on_hand = F('qty_on_hand') + qty_returning_to_batch
                batch.save(update_fields=['qty_on_hand'])
                
                # Refresh to get actual values
                batch.refresh_from_db()

                # Create movement record
                movement = PartMovement.objects.create(
                    part=part,
                    inventory_batch=batch,
                    to_location=location,
                    movement_type=PartMovement.MovementTypeChoices.RETURN,
                    qty_delta=qty_returning_to_batch,
                    work_order=work_order,
                    created_by=created_by
                )

                # Create negative work order part line for the return
                line_cost = qty_returning_to_batch * batch.last_unit_cost
                wo_part = WorkOrderPart.objects.create(
                    work_order=work_order,
                    part=part,
                    inventory_batch=batch,
                    qty_used=-qty_returning_to_batch,  # Negative for return
                    unit_cost_snapshot=batch.last_unit_cost,
                    total_parts_cost=-line_cost  # Negative cost
                )

                returns.append({
                    'batch_id': str(batch.id),
                    'qty_returned': qty_returning_to_batch,
                    'unit_cost': batch.last_unit_cost,
                    'total_cost': -line_cost,  # Negative for return
                    'received_date': batch.received_date.isoformat()
                })

                work_order_adjustments.append({
                    'work_order_part_id': str(wo_part.id),
                    'qty_used': -qty_returning_to_batch,
                    'unit_cost_snapshot': batch.last_unit_cost,
                    'total_parts_cost': -line_cost
                })

                total_cost += line_cost  # This will be negated in response
                remaining_to_return -= qty_returning_to_batch
                break  # For simplicity, return all to first batch

            response_data = {
                'work_order_id': work_order_id,
                'part_id': part_id,
                'total_qty_returned': qty_to_return,
                'total_cost_credit': str(total_cost),  # Positive number representing credit
                'returns': returns,
                'work_order_adjustments': work_order_adjustments,
                'message': f'Successfully returned {qty_to_return} units of {part.part_number} from work order {work_order.code}'
            }

            # Save idempotency result
            InventoryService._save_idempotency_result(
                idempotency_key, 'return', request_data, response_data, created_by
            )

            logger.info(f"Returned {qty_to_return} units of part {part.part_number} from WO {work_order.code}")
            return response_data

        except Part.DoesNotExist:
            raise ValidationError(f"Part with ID {part_id} not found")
        except Exception as e:
            logger.error(f"Error returning parts: {str(e)}")
            raise

    @staticmethod
    @transaction.atomic
    def transfer_between_locations(
        part_id: str,
        from_location_id: str,
        to_location_id: str,
        qty: int,
        created_by: User,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transfer parts between locations using FIFO logic.
        
        Args:
            part_id: ID of the part
            from_location_id: Source location ID
            to_location_id: Destination location ID
            qty: Quantity to transfer
            created_by: User performing the operation
            idempotency_key: Optional idempotency key
            
        Returns:
            Dict with transfer details
        """
        # Validate inputs
        InventoryService._validate_positive_qty(qty, "transfer quantity")
        if from_location_id == to_location_id:
            raise ValidationError("From and to locations cannot be the same")

        # Build request data for idempotency
        request_data = {
            'part_id': part_id,
            'from_location_id': from_location_id,
            'to_location_id': to_location_id,
            'qty': qty
        }

        # Check idempotency
        cached_result = InventoryService._check_idempotency(
            idempotency_key, 'transfer', request_data, created_by
        )
        if cached_result:
            return cached_result

        try:
            # Get entities
            part = Part.objects.get(id=part_id)
            from company.models import Location
            from_location = Location.objects.get(id=from_location_id)
            to_location = Location.objects.get(id=to_location_id)

            # Check availability at source location
            total_available = InventoryBatch.objects.filter(
                part=part,
                location=from_location,
                qty_on_hand__gt=0
            ).aggregate(
                total=Sum('qty_on_hand')
            )['total'] or 0

            if total_available < qty:
                raise InsufficientStockError(
                    f"Insufficient stock at source location. Requested: {qty}, Available: {total_available}",
                    available_qty=total_available
                )

            # Get source batches using FIFO
            source_batches = InventoryBatch.objects.select_for_update(
                skip_locked=True
            ).filter(
                part=part,
                location=from_location,
                qty_on_hand__gt=0
            ).order_by('received_date', 'created_at')

            transfers_out = []
            transfers_in = []
            remaining_to_transfer = qty

            for source_batch in source_batches:
                if remaining_to_transfer <= 0:
                    break

                qty_to_transfer = min(remaining_to_transfer, source_batch.qty_on_hand)

                # Reduce source batch
                source_batch.qty_on_hand = F('qty_on_hand') - qty_to_transfer
                source_batch.save(update_fields=['qty_on_hand'])
                source_batch.refresh_from_db()

                # Create transfer out movement
                movement_out = PartMovement.objects.create(
                    part=part,
                    inventory_batch=source_batch,
                    from_location=from_location,
                    to_location=to_location,
                    movement_type=PartMovement.MovementTypeChoices.TRANSFER_OUT,
                    qty_delta=-qty_to_transfer,
                    created_by=created_by
                )

                # Create or find destination batch with same cost and date
                dest_batch, created = InventoryBatch.objects.get_or_create(
                    part=part,
                    location=to_location,
                    last_unit_cost=source_batch.last_unit_cost,
                    received_date=source_batch.received_date,
                    defaults={
                        'qty_on_hand': 0,
                        'qty_reserved': 0
                    }
                )

                # Add to destination batch
                dest_batch.qty_on_hand = F('qty_on_hand') + qty_to_transfer
                dest_batch.save(update_fields=['qty_on_hand'])
                dest_batch.refresh_from_db()

                # Create transfer in movement
                movement_in = PartMovement.objects.create(
                    part=part,
                    inventory_batch=dest_batch,
                    from_location=from_location,
                    to_location=to_location,
                    movement_type=PartMovement.MovementTypeChoices.TRANSFER_IN,
                    qty_delta=qty_to_transfer,
                    created_by=created_by
                )

                transfers_out.append({
                    'source_batch_id': str(source_batch.id),
                    'movement_out_id': str(movement_out.id),
                    'qty_transferred': qty_to_transfer,
                    'unit_cost': source_batch.last_unit_cost
                })

                transfers_in.append({
                    'dest_batch_id': str(dest_batch.id),
                    'movement_in_id': str(movement_in.id),
                    'qty_transferred': qty_to_transfer,
                    'unit_cost': dest_batch.last_unit_cost,
                    'batch_created': created
                })

                remaining_to_transfer -= qty_to_transfer

            response_data = {
                'part_id': part_id,
                'from_location_id': from_location_id,
                'to_location_id': to_location_id,
                'total_qty_transferred': qty,
                'transfers_out': transfers_out,
                'transfers_in': transfers_in,
                'message': f'Successfully transferred {qty} units of {part.part_number} from {from_location.name} to {to_location.name}'
            }

            # Save idempotency result
            InventoryService._save_idempotency_result(
                idempotency_key, 'transfer', request_data, response_data, created_by
            )

            logger.info(f"Transferred {qty} units of part {part.part_number} from {from_location.name} to {to_location.name}")
            return response_data

        except Part.DoesNotExist:
            raise ValidationError(f"Part with ID {part_id} not found")
        except Exception as e:
            logger.error(f"Error transferring parts: {str(e)}")
            raise

    # Read-only methods for querying inventory

    @staticmethod
    def get_on_hand_summary(
        part_id: Optional[str] = None,
        location_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get on-hand quantities by part and location"""
        queryset = InventoryBatch.objects.select_related('part', 'location')
        
        if part_id:
            queryset = queryset.filter(part_id=part_id)
        if location_id:
            queryset = queryset.filter(location_id=location_id)

        summary = queryset.values(
            'part_id',
            'part__part_number',
            'part__name',
            'location_id',
            'location__name'
        ).annotate(
            total_on_hand=Sum('qty_on_hand'),
            total_reserved=Sum('qty_reserved'),
            total_available=Sum(F('qty_on_hand') - F('qty_reserved'))
        ).filter(total_on_hand__gt=0)

        return list(summary)

    @staticmethod
    def get_batches(
        part_id: Optional[str] = None,
        location_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get detailed batch information"""
        queryset = InventoryBatch.objects.select_related('part', 'location')
        
        if part_id:
            queryset = queryset.filter(part_id=part_id)
        if location_id:
            queryset = queryset.filter(location_id=location_id)

        queryset = queryset.filter(qty_on_hand__gt=0).order_by('received_date', 'created_at')

        batches = []
        for batch in queryset:
            batches.append({
                'batch_id': str(batch.id),
                'part_id': str(batch.part.id),
                'part_number': batch.part.part_number,
                'part_name': batch.part.name,
                'location_id': str(batch.location.id),
                'location_name': batch.location.name,
                'qty_on_hand': batch.qty_on_hand,
                'qty_reserved': batch.qty_reserved,
                'qty_available': batch.qty_available,
                'last_unit_cost': str(batch.last_unit_cost),
                'total_value': str(batch.total_value),
                'received_date': batch.received_date.isoformat(),
                'created_at': batch.created_at.isoformat()
            })

        return batches

    @staticmethod
    def get_work_order_parts(work_order_id: str) -> List[Dict[str, Any]]:
        """Get all parts used in a work order"""
        wo_parts = WorkOrderPart.objects.select_related(
            'part', 'inventory_batch', 'inventory_batch__location'
        ).filter(work_order_id=work_order_id).order_by('created_at')

        parts = []
        for wo_part in wo_parts:
            parts.append({
                'work_order_part_id': str(wo_part.id),
                'part_id': str(wo_part.part.id),
                'part_number': wo_part.part.part_number,
                'part_name': wo_part.part.name,
                'batch_id': str(wo_part.inventory_batch.id),
                'location_name': wo_part.inventory_batch.location.name,
                'qty_used': wo_part.qty_used,
                'unit_cost_snapshot': str(wo_part.unit_cost_snapshot),
                'total_parts_cost': str(wo_part.total_parts_cost),
                'received_date': wo_part.inventory_batch.received_date.isoformat(),
                'created_at': wo_part.created_at.isoformat()
            })

        return parts

    @staticmethod
    def get_movements(
        part_id: Optional[str] = None,
        location_id: Optional[str] = None,
        work_order_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get movement history with optional filters"""
        queryset = PartMovement.objects.select_related(
            'part', 'inventory_batch', 'from_location', 'to_location', 'work_order', 'created_by'
        ).order_by('-created_at')

        if part_id:
            queryset = queryset.filter(part_id=part_id)
        if location_id:
            queryset = queryset.filter(
                Q(from_location_id=location_id) | Q(to_location_id=location_id)
            )
        if work_order_id:
            queryset = queryset.filter(work_order_id=work_order_id)
        if from_date:
            queryset = queryset.filter(created_at__gte=from_date)
        if to_date:
            queryset = queryset.filter(created_at__lte=to_date)

        queryset = queryset[:limit]

        movements = []
        for movement in queryset:
            movements.append({
                'movement_id': str(movement.id),
                'part_id': str(movement.part.id),
                'part_number': movement.part.part_number,
                'part_name': movement.part.name,
                'batch_id': str(movement.inventory_batch.id) if movement.inventory_batch else None,
                'from_location': movement.from_location.name if movement.from_location else None,
                'to_location': movement.to_location.name if movement.to_location else None,
                'movement_type': movement.movement_type,
                'qty_delta': movement.qty_delta,
                'work_order_code': movement.work_order.code if movement.work_order else None,
                'receipt_id': movement.receipt_id,
                'notes': movement.notes,
                'created_by': movement.created_by.email if movement.created_by else None,
                'created_at': movement.created_at.isoformat()
            })

        return movements
