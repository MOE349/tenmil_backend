from rest_framework import status
from datetime import datetime
from django.core.exceptions import ValidationError
from configurations.base_features.views.base_api_view import BaseAPIView
from configurations.base_features.exceptions.base_exceptions import LocalBaseException
from parts.models import Part, InventoryBatch, WorkOrderPart, PartMovement
from parts.platforms.base.serializers import *
from parts.services import inventory_service, InsufficientStockError, InvalidOperationError


class PartBaseView(BaseAPIView):
    """Base view for Part CRUD operations"""
    serializer_class = PartBaseSerializer
    model_class = Part


class InventoryBatchBaseView(BaseAPIView):
    """Base view for InventoryBatch CRUD operations"""
    serializer_class = InventoryBatchBaseSerializer
    model_class = InventoryBatch
    
    def create(self, data, params, return_instance=False, *args, **kwargs):
        """Create InventoryBatch using enhanced service layer"""
        try:
            # Get user from params (set by handle_post_params)
            created_by = params.get('user')
            
            # Use enhanced service layer that handles all validation and logic
            result = inventory_service.receive_parts_from_data(
                data=data,
                created_by=created_by
            )
            
            if not result.success:
                raise LocalBaseException(
                    exception=result.message,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get the created batch
            batch_id = result.allocations[0].batch_id if result.allocations else None
            if not batch_id:
                raise LocalBaseException(
                    exception="Failed to create inventory batch",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Get the created instance and serialize it
            instance = InventoryBatch.objects.get(id=batch_id)
            serializer = self.serializer_class(instance)
            
            if return_instance:
                return instance, serializer.data
            return self.format_response(data=serializer.data, status_code=201)
            
        except (ValidationError, InvalidOperationError) as e:
            raise LocalBaseException(
                exception=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return self.handle_exception(e)
    
    def get_request_params(self, request):
        """Override to add null filtering for missing aisle, row, bin parameters"""
        params = super().get_request_params(request)
        
        # Get storage location parameters
        aisle = request.query_params.get('aisle')
        row = request.query_params.get('row')
        bin_param = request.query_params.get('bin')
        
        # Apply null filtering rule for missing parameters
        if aisle is not None:
            if aisle.strip() == '':
                params['aisle__isnull'] = True
            else:
                params['aisle'] = aisle
        else:
            # If aisle not provided, only get records with null aisle
            params['aisle__isnull'] = True
        
        if row is not None:
            if row.strip() == '':
                params['row__isnull'] = True
            else:
                params['row'] = row
        else:
            # If row not provided, only get records with null row
            params['row__isnull'] = True
        
        if bin_param is not None:
            if bin_param.strip() == '':
                params['bin__isnull'] = True
            else:
                params['bin'] = bin_param
        else:
            # If bin not provided, only get records with null bin
            params['bin__isnull'] = True
        
        return params


class WorkOrderPartBaseView(BaseAPIView):
    """Base view for WorkOrderPart CRUD operations"""
    serializer_class = WorkOrderPartBaseSerializer
    model_class = WorkOrderPart
    
    def create(self, data, params, return_instance=False, *args, **kwargs):
        """Create WorkOrderPart with FIFO inventory allocation"""
        try:
            from decimal import Decimal
            from django.db import transaction
            from work_orders.models import WorkOrder
            
            with transaction.atomic():
                # Get work order and determine location
                work_order_id = data.get('work_order')
                if not work_order_id:
                    raise LocalBaseException(
                        exception="work_order field is required",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                try:
                    work_order = WorkOrder.objects.get(id=work_order_id)
                except WorkOrder.DoesNotExist:
                    raise LocalBaseException(
                        exception="Work order not found",
                        status_code=status.HTTP_404_NOT_FOUND
                    )
                
                # Get location from work order's asset using GenericForeignKey resolution
                from configurations.base_features.db.db_helpers import get_object_by_content_type_and_id
                
                try:
                    asset = get_object_by_content_type_and_id(
                        work_order.content_type.id, 
                        str(work_order.object_id)
                    )
                except Exception as e:
                    raise LocalBaseException(
                        exception="Work order asset not found",
                        status_code=status.HTTP_404_NOT_FOUND
                    )
                
                if not hasattr(asset, 'location') or not asset.location:
                    raise LocalBaseException(
                        exception="Work order asset does not have a valid location",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                location = asset.location
                
                # Get part and validate
                part_id = data.get('part')
                if not part_id:
                    raise LocalBaseException(
                        exception="part field is required",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                try:
                    part = Part.objects.get(id=part_id)
                except Part.DoesNotExist:
                    raise LocalBaseException(
                        exception="Part not found",
                        status_code=status.HTTP_404_NOT_FOUND
                    )
                
                # Get qty_used from data
                qty_used = data.get('qty_used')
                if not qty_used:
                    raise LocalBaseException(
                        exception="qty_used field is required",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                try:
                    qty_used = int(qty_used)
                    if qty_used <= 0:
                        raise LocalBaseException(
                            exception="qty_used must be a positive integer",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                except (ValueError, TypeError):
                    raise LocalBaseException(
                        exception="qty_used must be a valid positive integer",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                # Get inventory batches for this part and location, ordered by received_date (FIFO)
                available_batches = InventoryBatch.objects.filter(
                    part=part,
                    location=location,
                    qty_on_hand__gt=0
                ).order_by('received_date')
                
                if not available_batches.exists():
                    raise LocalBaseException(
                        exception=f"No inventory available for part {part.part_number} at location {location.name}",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                # Check if we have enough total inventory
                total_available = sum(batch.qty_on_hand for batch in available_batches)
                if total_available < qty_used:
                    raise LocalBaseException(
                        exception=f"Insufficient inventory. Requested: {qty_used}, Available: {total_available}",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                # Allocate inventory using FIFO
                work_order_parts = []
                remaining_qty = qty_used
                
                for batch in available_batches:
                    if remaining_qty <= 0:
                        break
                    
                    # Determine how much to take from this batch
                    qty_from_batch = min(remaining_qty, batch.qty_on_hand)
                    
                    # Create WorkOrderPart record for this batch
                    work_order_part = WorkOrderPart.objects.create(
                        work_order=work_order,
                        part=part,
                        inventory_batch=batch,
                        qty_used=qty_from_batch,
                        unit_cost_snapshot=batch.last_unit_cost,
                        total_parts_cost=qty_from_batch * batch.last_unit_cost
                    )
                    work_order_parts.append(work_order_part)
                    
                    # Update inventory batch qty_on_hand
                    batch.qty_on_hand -= qty_from_batch
                    batch.save(update_fields=['qty_on_hand'])
                    
                    # Create movement record for audit trail
                    PartMovement.objects.create(
                        part=part,
                        inventory_batch=batch,
                        from_location=location,
                        to_location=None,  # Parts are consumed, not transferred
                        movement_type=PartMovement.MovementType.ISSUE,
                        qty_delta=-qty_from_batch,
                        work_order=work_order,
                        created_by=params.get('user')
                    )
                    
                    remaining_qty -= qty_from_batch
                
                # Return response with all created work order parts
                serialized_data = []
                for wop in work_order_parts:
                    serializer = self.serializer_class(wop)
                    serialized_data.append(serializer.data)
                
                if return_instance:
                    return work_order_parts, serialized_data
                
                return self.format_response(
                    data={
                        'work_order_parts': serialized_data,
                        'total_qty_used': str(qty_used),
                        'batches_used': len(work_order_parts),
                        'location': {
                            'id': str(location.id),
                            'name': location.name
                        }
                    }, 
                    status_code=201
                )
        
        except Exception as e:
            return self.handle_exception(e)
    
    # def list(self, params, *args, **kwargs):
    #     """Get list of WorkOrderParts aggregated by part and work_order"""
    #     from django.db.models import Sum
    #     from parts.platforms.base.serializers import PartBaseSerializer
    #     from work_orders.models import WorkOrder
        
    #     try:
    #         # Get base queryset
    #         ordering_by = None
    #         if "ordering" in params:
    #             ordering_by = params.pop('ordering')
    #         user_lang = params.pop('lang', 'en')
            
    #         # Get the filtered queryset but aggregate by part and work_order
    #         base_queryset = self.get_queryset(params=params, ordering=ordering_by)
            
    #         # Aggregate by part and work_order, summing qty_used
    #         aggregated_data = (base_queryset
    #             .values('part', 'work_order')
    #             .annotate(total_qty_used=Sum('qty_used'))
    #             .order_by('work_order', 'part'))
            
    #         # Build response data
    #         response_data = []
    #         for item in aggregated_data:
    #             # Get the part object for serialization
    #             try:
    #                 part = Part.objects.get(id=item['part'])
    #                 work_order = WorkOrder.objects.get(id=item['work_order'])
                    
    #                 # Serialize the part
    #                 part_serializer = PartBaseSerializer(part)
                    
    #                 response_item = {
    #                     'part': part_serializer.data,
    #                     'work_order': {
    #                         'id': str(work_order.id),
    #                         'code': work_order.code,
    #                         'end_point': '/work_orders/work_order'
    #                     },
    #                     'qty_used': str(item['total_qty_used'])
    #                 }
    #                 response_data.append(response_item)
                    
    #             except (Part.DoesNotExist, WorkOrder.DoesNotExist):
    #                 continue  # Skip invalid records
            
    #         return self.format_response(data=response_data, status_code=200)
            
    #     except Exception as e:
    #         return self.handle_exception(e)
    
    def update(self, data, params, pk=None, *args, **kwargs):
        """Update WorkOrderPart with proper inventory batch adjustment and movement logging"""
        try:
            from decimal import Decimal
            from django.db import transaction
            from work_orders.models import WorkOrder
            
            with transaction.atomic():
                # Get the existing WorkOrderPart instance
                if not pk:
                    raise LocalBaseException(
                        exception="Primary key is required for update",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                try:
                    work_order_part = WorkOrderPart.objects.select_related(
                        'work_order', 'part', 'inventory_batch', 'inventory_batch__location'
                    ).get(id=pk)
                except WorkOrderPart.DoesNotExist:
                    raise LocalBaseException(
                        exception="Work order part not found",
                        status_code=status.HTTP_404_NOT_FOUND
                    )
                
                # Get the old and new qty_used values
                old_qty_used = work_order_part.qty_used
                new_qty_used = data.get('qty_used', old_qty_used)
                
                # If qty_used hasn't changed, proceed with regular update
                if old_qty_used == new_qty_used:
                    # Just update other fields (like unit_cost_snapshot)
                    serializer = self.serializer_class(work_order_part, data=data, partial=True)
                    if not serializer.is_valid():
                        raise LocalBaseException(
                            exception=serializer.errors,
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                    
                    updated_instance = serializer.save()
                    return self.format_response(data=serializer.data, status_code=200)
                
                # Validate new_qty_used
                try:
                    new_qty_used = int(new_qty_used)
                    if new_qty_used <= 0:
                        raise LocalBaseException(
                            exception="qty_used must be a positive integer",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                except (ValueError, TypeError):
                    raise LocalBaseException(
                        exception="qty_used must be a valid positive integer",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                # Get work order and location for inventory operations
                work_order = work_order_part.work_order
                part = work_order_part.part
                location = work_order_part.inventory_batch.location
                
                qty_difference = new_qty_used - old_qty_used
                
                if qty_difference > 0:
                    # Need to issue more parts using FIFO
                    return self._handle_qty_increase(
                        work_order_part, qty_difference, data, params
                    )
                else:
                    # Need to return parts using LIFO  
                    return self._handle_qty_decrease(
                        work_order_part, abs(qty_difference), data, params
                    )
        
        except Exception as e:
            return self.handle_exception(e)
    
    def _handle_qty_increase(self, work_order_part, qty_increase, data, params):
        """Handle increase in qty_used by issuing more parts using FIFO"""
        from decimal import Decimal
        
        work_order = work_order_part.work_order
        part = work_order_part.part
        location = work_order_part.inventory_batch.location
        
        # Get available inventory batches using FIFO (oldest first)
        available_batches = InventoryBatch.objects.filter(
            part=part,
            location=location,
            qty_on_hand__gt=0
        ).order_by('received_date')
        
        # Check if we have enough total inventory
        total_available = sum(batch.qty_on_hand for batch in available_batches)
        if total_available < qty_increase:
            raise LocalBaseException(
                exception=f"Insufficient inventory for increase. Requested: {qty_increase}, Available: {total_available}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Allocate inventory using FIFO
        remaining_qty = qty_increase
        allocated_batches = []
        
        for batch in available_batches:
            if remaining_qty <= 0:
                break
            
            # Determine how much to take from this batch
            qty_from_batch = min(remaining_qty, batch.qty_on_hand)
            
            # Update inventory batch qty_on_hand
            batch.qty_on_hand -= qty_from_batch
            batch.save(update_fields=['qty_on_hand'])
            
            # Create movement record for audit trail
            PartMovement.objects.create(
                part=part,
                inventory_batch=batch,
                from_location=location,
                to_location=None,  # Parts are consumed, not transferred
                movement_type=PartMovement.MovementType.ISSUE,
                qty_delta=-qty_from_batch,
                work_order=work_order,
                created_by=params.get('user')
            )
            
            allocated_batches.append({
                'batch': batch,
                'qty_allocated': qty_from_batch
            })
            
            remaining_qty -= qty_from_batch
        
        # If the increase is from the same batch as the original, just update that WorkOrderPart
        original_batch = work_order_part.inventory_batch
        same_batch_allocation = next(
            (alloc for alloc in allocated_batches if alloc['batch'].id == original_batch.id), 
            None
        )
        
        if same_batch_allocation and len(allocated_batches) == 1:
            # Simple case: all additional qty from same batch
            work_order_part.qty_used += qty_increase
            work_order_part.total_parts_cost = work_order_part.qty_used * work_order_part.unit_cost_snapshot
            
            # Update other fields if provided
            for field, value in data.items():
                if field not in ['qty_used'] and hasattr(work_order_part, field):
                    setattr(work_order_part, field, value)
            
            work_order_part.save()
            
            serializer = self.serializer_class(work_order_part)
            return self.format_response(
                data={
                    'updated_work_order_part': serializer.data,
                    'qty_increase': str(qty_increase),
                    'allocation_method': 'same_batch'
                },
                status_code=200
            )
        else:
            # Complex case: need multiple batches, create additional WorkOrderPart records
            # Keep original record unchanged, create new records for additional allocations
            additional_records = []
            
            for allocation in allocated_batches:
                if allocation['batch'].id == original_batch.id:
                    # Update the original record
                    work_order_part.qty_used += allocation['qty_allocated']
                    work_order_part.total_parts_cost = work_order_part.qty_used * work_order_part.unit_cost_snapshot
                    work_order_part.save()
                else:
                    # Create new WorkOrderPart record
                    new_record = WorkOrderPart.objects.create(
                        work_order=work_order,
                        part=part,
                        inventory_batch=allocation['batch'],
                        qty_used=allocation['qty_allocated'],
                        unit_cost_snapshot=allocation['batch'].last_unit_cost,
                        total_parts_cost=allocation['qty_allocated'] * allocation['batch'].last_unit_cost
                    )
                    additional_records.append(new_record)
            
            # Update other fields in original record if provided
            for field, value in data.items():
                if field not in ['qty_used'] and hasattr(work_order_part, field):
                    setattr(work_order_part, field, value)
            work_order_part.save()
            
            # Serialize all records
            serialized_data = []
            serializer = self.serializer_class(work_order_part)
            serialized_data.append(serializer.data)
            
            for record in additional_records:
                serializer = self.serializer_class(record)
                serialized_data.append(serializer.data)
            
            return self.format_response(
                data={
                    'work_order_parts': serialized_data,
                    'qty_increase': str(qty_increase),
                    'batches_allocated': len(allocated_batches),
                    'allocation_method': 'multiple_batches'
                },
                status_code=200
            )
    
    def _handle_qty_decrease(self, work_order_part, qty_decrease, data, params):
        """Handle decrease in qty_used by returning parts using LIFO"""
        from decimal import Decimal
        
        work_order = work_order_part.work_order
        part = work_order_part.part
        
        # Get all WorkOrderPart records for this work_order and part
        # Order by created_at DESC for LIFO (return most recent issues first)
        work_order_parts = WorkOrderPart.objects.filter(
            work_order=work_order,
            part=part,
            qty_used__gt=0  # Only positive quantities (issued parts)
        ).order_by('-created_at')
        
        if not work_order_parts.exists():
            raise LocalBaseException(
                exception="No issued parts found for this work order and part combination",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Calculate current total issued quantity
        total_issued = sum(wop.qty_used for wop in work_order_parts)
        
        # Validate we have enough to return
        if total_issued < qty_decrease:
            raise LocalBaseException(
                exception=f"Cannot return more than issued. Current: {total_issued}, Requested to decrease by: {qty_decrease}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Process returns using LIFO
        remaining_to_return = qty_decrease
        returned_records = []
        
        for wop in work_order_parts:
            if remaining_to_return <= 0:
                break
            
            # Determine how much to return from this record
            qty_from_this_record = min(remaining_to_return, wop.qty_used)
            
            # Update inventory batch (add back to qty_on_hand)
            inventory_batch = wop.inventory_batch
            inventory_batch.qty_on_hand += qty_from_this_record
            inventory_batch.save(update_fields=['qty_on_hand'])
            
            # Create return movement record for audit trail
            PartMovement.objects.create(
                part=part,
                inventory_batch=inventory_batch,
                from_location=None,  # Parts are being returned, not transferred from
                to_location=inventory_batch.location,
                movement_type=PartMovement.MovementType.RETURN,
                qty_delta=qty_from_this_record,  # Positive for returns
                work_order=work_order,
                created_by=params.get('user')
            )
            
            # Update or delete the WorkOrderPart record
            if qty_from_this_record == wop.qty_used:
                # Full return - delete the record
                returned_records.append({
                    'work_order_part_id': str(wop.id),
                    'inventory_batch_id': str(inventory_batch.id),
                    'qty_returned': str(qty_from_this_record),
                    'action': 'deleted'
                })
                wop.delete()
            else:
                # Partial return - update the record
                wop.qty_used -= qty_from_this_record
                wop.total_parts_cost = wop.qty_used * wop.unit_cost_snapshot
                
                # Update other fields if this is the record being updated and it still exists
                if wop.id == work_order_part.id:
                    for field, value in data.items():
                        if field not in ['qty_used'] and hasattr(wop, field):
                            setattr(wop, field, value)
                
                wop.save()
                
                returned_records.append({
                    'work_order_part_id': str(wop.id),
                    'inventory_batch_id': str(inventory_batch.id),
                    'qty_returned': str(qty_from_this_record),
                    'remaining_qty_used': str(wop.qty_used),
                    'action': 'updated'
                })
            
            remaining_to_return -= qty_from_this_record
        
        # Get the updated/remaining WorkOrderPart records
        updated_records = WorkOrderPart.objects.filter(
            work_order=work_order,
            part=part,
            qty_used__gt=0
        ).order_by('-created_at')
        
        # Serialize remaining records
        serialized_data = []
        for record in updated_records:
            serializer = self.serializer_class(record)
            serialized_data.append(serializer.data)
        
        return self.format_response(
            data={
                'operation': 'qty_decrease',
                'work_order_parts': serialized_data,
                'qty_decrease': str(qty_decrease),
                'records_processed': len(returned_records),
                'returned_records': returned_records
            },
            status_code=200
        )

    def return_parts_to_inventory(self, request):
        """Return parts from work order back to inventory using LIFO"""
        try:
            from decimal import Decimal
            from django.db import transaction
            from work_orders.models import WorkOrder
            from rest_framework import status
            
            with transaction.atomic():
                # Get request data
                work_order_id = request.data.get('work_order_id')
                part_id = request.data.get('part_id') 
                new_qty_used = request.data.get('qty_used')  # This is the desired FINAL amount
                explicit_return_qty = request.data.get('qty_to_return')  # This is explicit return amount
                
                # Validate inputs
                if not work_order_id:
                    raise LocalBaseException(
                        exception="work_order_id is required",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                if not part_id:
                    raise LocalBaseException(
                        exception="part_id is required",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                if not new_qty_used and not explicit_return_qty:
                    raise LocalBaseException(
                        exception="Either qty_used (final amount) or qty_to_return (return amount) is required",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                # Validate work order and part exist
                try:
                    work_order = WorkOrder.objects.get(id=work_order_id)
                    part = Part.objects.get(id=part_id)
                except (WorkOrder.DoesNotExist, Part.DoesNotExist):
                    raise LocalBaseException(
                        exception="Work order or part not found",
                        status_code=status.HTTP_404_NOT_FOUND
                    )
                
                # Get all WorkOrderPart records for this work_order and part
                # Order by created_at DESC for LIFO (return most recent issues first)
                work_order_parts = WorkOrderPart.objects.filter(
                    work_order=work_order,
                    part=part,
                    qty_used__gt=0  # Only positive quantities (issued parts)
                ).order_by('-created_at')
                
                if not work_order_parts.exists():
                    raise LocalBaseException(
                        exception="No issued parts found for this work order and part combination",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                # Calculate current total issued quantity
                total_issued = sum(wop.qty_used for wop in work_order_parts)
                
                # Determine how much to return
                if explicit_return_qty is not None:
                    # Direct return amount specified
                    try:
                        qty_to_return = int(explicit_return_qty)
                        if qty_to_return <= 0:
                            raise LocalBaseException(
                                exception="qty_to_return must be a positive value",
                                status_code=status.HTTP_400_BAD_REQUEST
                            )
                    except (ValueError, TypeError):
                        raise LocalBaseException(
                            exception="qty_to_return must be a valid positive integer",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                else:
                    # Calculate return amount from desired final qty_used
                    try:
                        new_qty_used = int(new_qty_used)
                        if new_qty_used < 0:
                            raise LocalBaseException(
                                exception="qty_used (final amount) cannot be negative",
                                status_code=status.HTTP_400_BAD_REQUEST
                            )
                    except (ValueError, TypeError):
                        raise LocalBaseException(
                            exception="qty_used must be a valid positive integer",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                    if new_qty_used > total_issued:
                        raise LocalBaseException(
                            exception=f"Cannot set qty_used higher than current amount. Current: {total_issued}, Requested: {new_qty_used}",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                    qty_to_return = total_issued - new_qty_used
                    
                    # If no return needed, return early
                    if qty_to_return == 0:
                        return self.format_response(
                            data={
                                'message': 'No return needed - qty_used is already at the requested amount',
                                'current_qty_used': str(total_issued)
                            },
                            status_code=200
                        )
                
                # Validate we have enough to return
                if total_issued < qty_to_return:
                    raise LocalBaseException(
                        exception=f"Cannot return more than issued. Current: {total_issued}, Requested: {qty_to_return}",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                # Process returns using LIFO
                remaining_to_return = qty_to_return
                returned_records = []
                
                for wop in work_order_parts:
                    if remaining_to_return <= 0:
                        break
                    
                    # Determine how much to return from this record
                    qty_from_this_record = min(remaining_to_return, wop.qty_used)
                    
                    # Update inventory batch (add back to qty_on_hand)
                    inventory_batch = wop.inventory_batch
                    inventory_batch.qty_on_hand += qty_from_this_record
                    inventory_batch.save(update_fields=['qty_on_hand'])
                    
                    # Create return movement record for audit trail
                    PartMovement.objects.create(
                        part=part,
                        inventory_batch=inventory_batch,
                        from_location=None,  # Parts are being returned, not transferred from
                        to_location=inventory_batch.location,
                        movement_type=PartMovement.MovementType.RETURN,
                        qty_delta=qty_from_this_record,  # Positive for returns
                        work_order=work_order,
                        created_by=request.user
                    )
                    
                    # Update or delete the WorkOrderPart record
                    if qty_from_this_record == wop.qty_used:
                        # Full return - delete the record
                        returned_records.append({
                            'work_order_part_id': str(wop.id),
                            'inventory_batch_id': str(inventory_batch.id),
                            'qty_returned': str(qty_from_this_record),
                            'action': 'deleted'
                        })
                        wop.delete()
                    else:
                        # Partial return - update the record
                        wop.qty_used -= qty_from_this_record
                        wop.total_parts_cost = wop.qty_used * wop.unit_cost_snapshot
                        wop.save(update_fields=['qty_used', 'total_parts_cost'])
                        
                        returned_records.append({
                            'work_order_part_id': str(wop.id),
                            'inventory_batch_id': str(inventory_batch.id),
                            'qty_returned': str(qty_from_this_record),
                            'remaining_qty_used': str(wop.qty_used),
                            'action': 'updated'
                        })
                    
                    remaining_to_return -= qty_from_this_record
                
                # Calculate final qty_used after returns
                final_qty_used = total_issued - qty_to_return
                
                # Return success response
                return self.format_response(
                    data={
                        'operation': 'return_parts',
                        'work_order': {
                            'id': str(work_order.id),
                            'code': work_order.code
                        },
                        'part': {
                            'id': str(part.id),
                            'part_number': part.part_number,
                            'name': part.name
                        },
                        'previous_qty_used': str(total_issued),
                        'qty_returned': str(qty_to_return),
                        'final_qty_used': str(final_qty_used),
                        'records_processed': len(returned_records),
                        'returned_records': returned_records
                    },
                    status_code=200
                )
        
        except Exception as e:
            return self.handle_exception(e)


class PartMovementBaseView(BaseAPIView):
    """Base view for PartMovement read-only operations"""
    serializer_class = PartMovementBaseSerializer
    model_class = PartMovement
    
    def get_request_params(self, request):
        """Override to handle inventory_batch positioning filters"""
        # Start with empty params to avoid processing positioning fields as model fields
        params = {}
        
        # Only get non-positioning parameters from the parent
        allowed_params = ['part', 'part_id', 'work_order', 'work_order_id', 'movement_type', 'from_date', 'to_date', 'limit']
        for param, value in request.query_params.items():
            if param in allowed_params and value:
                params[param] = value
        
        # Handle location filtering through multiple fields
        location_param = request.query_params.get('location')
        if location_param:
            from django.db.models import Q
            params['_custom_location_filter'] = Q(
                from_location__id=location_param
            ) | Q(
                to_location__id=location_param
            ) | Q(
                inventory_batch__location__id=location_param
            )
        
        # Handle positioning parameters through inventory_batch
        aisle = request.query_params.get('aisle')
        row = request.query_params.get('row')
        bin_param = request.query_params.get('bin')
        
        if aisle is not None:
            if aisle == '' or aisle == '0':
                # Handle default/empty values
                from django.db.models import Q
                params['_custom_aisle_filter'] = Q(
                    inventory_batch__aisle='0'
                ) | Q(
                    inventory_batch__aisle__isnull=True
                ) | Q(
                    inventory_batch__aisle=''
                )
            else:
                from django.db.models import Q
                params['_custom_aisle_filter'] = Q(inventory_batch__aisle=aisle)
        
        if row is not None:
            if row == '' or row == '0':
                # Handle default/empty values
                from django.db.models import Q
                params['_custom_row_filter'] = Q(
                    inventory_batch__row='0'
                ) | Q(
                    inventory_batch__row__isnull=True
                ) | Q(
                    inventory_batch__row=''
                )
            else:
                from django.db.models import Q
                params['_custom_row_filter'] = Q(inventory_batch__row=row)
        
        if bin_param is not None:
            if bin_param == '' or bin_param == '0':
                # Handle default/empty values
                from django.db.models import Q
                params['_custom_bin_filter'] = Q(
                    inventory_batch__bin='0'
                ) | Q(
                    inventory_batch__bin__isnull=True
                ) | Q(
                    inventory_batch__bin=''
                )
            else:
                from django.db.models import Q
                params['_custom_bin_filter'] = Q(inventory_batch__bin=bin_param)
        
        return params
    
    def list(self, params, *args, **kwargs):
        """Custom list method to handle complex filtering"""
        try:
            # Extract custom filters
            location_filter = params.pop('_custom_location_filter', None)
            aisle_filter = params.pop('_custom_aisle_filter', None)
            row_filter = params.pop('_custom_row_filter', None)
            bin_filter = params.pop('_custom_bin_filter', None)
            
            # Get base queryset
            queryset = self.model_class.objects.select_related(
                'part', 'from_location', 'to_location', 'work_order', 'inventory_batch', 'inventory_batch__location'
            )
            
            # Map and apply regular filters with proper field names
            django_filters = {}
            if 'part' in params:
                django_filters['part__id'] = params['part']
            elif 'part_id' in params:
                django_filters['part__id'] = params['part_id']
            
            if 'work_order' in params:
                django_filters['work_order__id'] = params['work_order']
            elif 'work_order_id' in params:
                django_filters['work_order__id'] = params['work_order_id']
            
            if 'movement_type' in params:
                django_filters['movement_type'] = params['movement_type']
            
            # Handle date filtering
            if 'from_date' in params:
                from datetime import datetime
                if isinstance(params['from_date'], str):
                    from_date = datetime.fromisoformat(params['from_date'].replace('Z', '+00:00'))
                else:
                    from_date = params['from_date']
                django_filters['created_at__gte'] = from_date
                
            if 'to_date' in params:
                from datetime import datetime
                if isinstance(params['to_date'], str):
                    to_date = datetime.fromisoformat(params['to_date'].replace('Z', '+00:00'))
                else:
                    to_date = params['to_date']
                django_filters['created_at__lte'] = to_date
            
            # Apply Django field filters
            if django_filters:
                queryset = queryset.filter(**django_filters)
            
            # Apply custom Q object filters
            if location_filter:
                queryset = queryset.filter(location_filter)
            if aisle_filter:
                queryset = queryset.filter(aisle_filter)
            if row_filter:
                queryset = queryset.filter(row_filter)
            if bin_filter:
                queryset = queryset.filter(bin_filter)
            
            # Apply ordering
            queryset = queryset.order_by('-created_at')
            
            # Handle limit
            limit = int(params.get('limit', 100))
            if limit > 0:
                queryset = queryset[:limit]
            
            # Serialize data
            serializer = self.serializer_class(queryset, many=True)
            return self.format_response(data=serializer.data, status_code=200)
            
        except Exception as e:
            return self.handle_exception(e)
    
    # Part movements are immutable - disable write operations
    def create(self, data, params, *args, **kwargs):
        try:
            raise LocalBaseException(
                exception="Part movements are immutable and created automatically",
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        except Exception as e:
            return self.handle_exception(e)
    
    def update(self, data, params, pk=None, *args, **kwargs):
        try:
            raise LocalBaseException(
                exception="Part movements are immutable",
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        except Exception as e:
            return self.handle_exception(e)
    
    def destroy(self, params, pk=None, *args, **kwargs):
        try:
            raise LocalBaseException(
                exception="Part movements are immutable",
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        except Exception as e:
            return self.handle_exception(e)


class InventoryOperationsBaseView(BaseAPIView):
    """Base view for inventory operations using service layer"""
    
    # No specific model/serializer as this handles operations
    model_class = None
    serializer_class = None
    
    def receive_parts(self, request):
        """Receive parts into inventory"""
        try:
            serializer = ReceivePartsSerializer(data=request.data)
            if not serializer.is_valid():
                return self.format_response(None, serializer.errors, status.HTTP_400_BAD_REQUEST)
            
            data = serializer.validated_data
            result = inventory_service.receive_parts(
                part_id=str(data['part_id']),
                location_id=str(data['location_id']),
                qty=data['qty'],
                unit_cost=data['unit_cost'],
                received_date=data.get('received_date'),
                receipt_id=data.get('receipt_id'),
                created_by=request.user,
                idempotency_key=data.get('idempotency_key')
            )
            
            return self.format_response(
                {
                    'operation': 'receive',
                    'success': result.success,
                    'message': result.message,
                    'allocations': [
                        {
                            'batch_id': alloc.batch_id,
                            'qty_allocated': str(alloc.qty_allocated),
                            'unit_cost': str(alloc.unit_cost),
                            'total_cost': str(alloc.total_cost)
                        } for alloc in result.allocations
                    ],
                    'movements': result.movements
                },
                None,
                status.HTTP_201_CREATED
            )
            
        except (InsufficientStockError, InvalidOperationError) as e:
            return self.format_response(None, [str(e)], status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return self.handle_exception(e)
    
    def issue_parts(self, request):
        """Issue parts to work order"""
        try:
            serializer = IssuePartsSerializer(data=request.data)
            if not serializer.is_valid():
                return self.format_response(None, serializer.errors, status.HTTP_400_BAD_REQUEST)
            
            data = serializer.validated_data
            result = inventory_service.issue_to_work_order(
                work_order_id=str(data['work_order_id']),
                part_id=str(data['part_id']),
                location_id=str(data['location_id']),
                qty_requested=data['qty'],
                created_by=request.user,
                idempotency_key=data.get('idempotency_key')
            )
            
            return self.format_response(
                {
                    'operation': 'issue',
                    'success': result.success,
                    'message': result.message,
                    'allocations': [
                        {
                            'batch_id': alloc.batch_id,
                            'qty_allocated': str(alloc.qty_allocated),
                            'unit_cost': str(alloc.unit_cost),
                            'total_cost': str(alloc.total_cost)
                        } for alloc in result.allocations
                    ],
                    'movements': result.movements,
                    'work_order_parts': result.work_order_parts
                },
                None,
                status.HTTP_200_OK
            )
            
        except InsufficientStockError as e:
            return self.format_response(
                None, 
                [f"Insufficient stock: requested {e.requested}, available {e.available}"], 
                status.HTTP_400_BAD_REQUEST
            )
        except (InvalidOperationError) as e:
            return self.format_response(None, [str(e)], status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return self.handle_exception(e)
    
    def return_parts(self, request):
        """Return parts from work order"""
        try:
            serializer = ReturnPartsSerializer(data=request.data)
            if not serializer.is_valid():
                return self.format_response(None, serializer.errors, status.HTTP_400_BAD_REQUEST)
            
            data = serializer.validated_data
            result = inventory_service.return_from_work_order(
                work_order_id=str(data['work_order_id']),
                part_id=str(data['part_id']),
                location_id=str(data['location_id']),
                qty_to_return=data['qty'],
                created_by=request.user,
                idempotency_key=data.get('idempotency_key')
            )
            
            return self.format_response(
                {
                    'operation': 'return',
                    'success': result.success,
                    'message': result.message,
                    'allocations': [
                        {
                            'batch_id': alloc.batch_id,
                            'qty_allocated': str(alloc.qty_allocated),
                            'unit_cost': str(alloc.unit_cost),
                            'total_cost': str(alloc.total_cost)
                        } for alloc in result.allocations
                    ],
                    'movements': result.movements,
                    'work_order_parts': result.work_order_parts
                },
                None,
                status.HTTP_200_OK
            )
            
        except (InvalidOperationError) as e:
            return self.format_response(None, [str(e)], status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return self.handle_exception(e)
    
    def transfer_parts(self, request):
        """Transfer parts between locations"""
        try:
            serializer = TransferPartsSerializer(data=request.data)
            if not serializer.is_valid():
                return self.format_response(None, serializer.errors, status.HTTP_400_BAD_REQUEST)
            
            data = serializer.validated_data
            result = inventory_service.transfer_between_locations(
                part_id=str(data['part_id']),
                from_location_id=str(data['from_location_id']),
                to_location_id=str(data['to_location_id']),
                qty=data['qty'],
                created_by=request.user,
                aisle=data.get('aisle'),
                row=data.get('row'),
                bin=data.get('bin'),
                from_aisle=data.get('from_aisle'),
                from_row=data.get('from_row'),
                from_bin=data.get('from_bin'),
                idempotency_key=data.get('idempotency_key')
            )
            
            return self.format_response(
                {
                    'operation': 'transfer',
                    'success': result.success,
                    'message': result.message,
                    'allocations': [
                        {
                            'batch_id': alloc.batch_id,
                            'qty_allocated': str(alloc.qty_allocated),
                            'unit_cost': str(alloc.unit_cost),
                            'total_cost': str(alloc.total_cost)
                        } for alloc in result.allocations
                    ],
                    'movements': result.movements
                },
                None,
                status.HTTP_200_OK
            )
            
        except InsufficientStockError as e:
            return self.format_response(
                None, 
                [f"Insufficient stock: requested {e.requested}, available {e.available}"], 
                status.HTTP_400_BAD_REQUEST
            )
        except (InvalidOperationError) as e:
            return self.format_response(None, [str(e)], status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return self.handle_exception(e)
    
    def get_on_hand(self, request):
        """Get detailed inventory batch information by part, location, and optional storage details"""
        try:
            # Get query parameters - support both parameter formats for backward compatibility
            part_id = request.query_params.get('part_id') or request.query_params.get('part')
            location_id = request.query_params.get('location_id') or request.query_params.get('location')
            aisle = request.query_params.get('aisle')
            row = request.query_params.get('row')
            bin_param = request.query_params.get('bin')
            
            # Validate required parameters
            if not part_id:
                raise LocalBaseException(
                    exception="part_id or part parameter is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            if not location_id:
                raise LocalBaseException(
                    exception="location_id or location parameter is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify part exists - try by ID first, then by part_number if ID fails
            try:
                # First try to get by ID (UUID)
                part = Part.objects.get(id=part_id)
            except (Part.DoesNotExist, ValueError) as e:
                if "badly formed hexadecimal UUID" in str(e) or "is not a valid UUID" in str(e):
                    # If UUID is invalid, try to find by part_number
                    try:
                        part = Part.objects.get(part_number=part_id)
                    except Part.DoesNotExist:
                        raise LocalBaseException(
                            exception=f"Part '{part_id}' not found by ID or part number",
                            status_code=status.HTTP_404_NOT_FOUND
                        )
                else:
                    raise LocalBaseException(
                        exception=f"Part with ID {part_id} does not exist",
                        status_code=status.HTTP_404_NOT_FOUND
                    )
            
            # Verify location exists - try by ID first, then by name if ID fails
            from company.models import Location
            try:
                # First try to get by ID (UUID)
                location = Location.objects.select_related('site').get(id=location_id)
            except (Location.DoesNotExist, ValueError) as e:
                if "badly formed hexadecimal UUID" in str(e) or "is not a valid UUID" in str(e):
                    # If UUID is invalid, try to find by name
                    try:
                        location = Location.objects.select_related('site').get(name=location_id)
                    except Location.DoesNotExist:
                        raise LocalBaseException(
                            exception=f"Location '{location_id}' not found by ID or name",
                            status_code=status.HTTP_404_NOT_FOUND
                        )
                else:
                    raise LocalBaseException(
                        exception=f"Location with ID {location_id} does not exist",
                        status_code=status.HTTP_404_NOT_FOUND
                    )
            
            # Build queryset with filters
            queryset = InventoryBatch.objects.filter(
                part=part,
                location=location
            )
            
            # Add filters for aisle, row, bin - if not provided, filter for null values
            if aisle is not None:
                if aisle.strip() == '':
                    queryset = queryset.filter(aisle__isnull=True)
                else:
                    queryset = queryset.filter(aisle=aisle)
            else:
                # If aisle not provided, only get records with null aisle
                queryset = queryset.filter(aisle__isnull=True)
            
            if row is not None:
                if row.strip() == '':
                    queryset = queryset.filter(row__isnull=True)
                else:
                    queryset = queryset.filter(row=row)
            else:
                # If row not provided, only get records with null row
                queryset = queryset.filter(row__isnull=True)
            
            if bin_param is not None:
                if bin_param.strip() == '':
                    queryset = queryset.filter(bin__isnull=True)
                else:
                    queryset = queryset.filter(bin=bin_param)
            else:
                # If bin not provided, only get records with null bin
                queryset = queryset.filter(bin__isnull=True)
            
            # Get all matching batches and calculate totals
            batches = queryset.all()
            
            if not batches:
                raise LocalBaseException(
                    exception="No inventory batches found matching the criteria",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Calculate total quantities
            total_qty_on_hand = sum(batch.qty_on_hand for batch in batches)
            total_qty_reserved = sum(batch.qty_reserved for batch in batches)
            
            # Get the newest batch for last_unit_cost (by received_date)
            newest_batch = max(batches, key=lambda b: b.received_date)
            
            # Use the first batch's location details (they should all be the same since we filtered by them)
            sample_batch = batches[0]
            
            # Prepare response data
            response_data = {
                'part_number': part.part_number,
                'part_name': part.name,
                'site': {
                    'id': str(location.site.id) if location.site else None,
                    'code': location.site.code if location.site else '',
                    'name': location.site.name if location.site else ''
                } if location.site else None,
                'location': {
                    'id': str(location.id),
                    'name': location.name
                },
                'aisle': sample_batch.aisle or '',
                'row': sample_batch.row or '',
                'bin': sample_batch.bin or '',
                'qty_on_hand': str(total_qty_on_hand),
                'qty_reserved': str(total_qty_reserved),
                'last_unit_cost': str(newest_batch.last_unit_cost),
                'batches_count': len(batches),
                'newest_received_date': newest_batch.received_date.isoformat()
            }
            
            return self.format_response(response_data, None, status.HTTP_200_OK)
            
        except Exception as e:
            return self.handle_exception(e)
    
    def get_batches(self, request):
        """Get inventory batches with optional filtering"""
        try:
            # Support both 'part' and 'part_id' parameters for backward compatibility
            part_id = request.query_params.get('part_id') or request.query_params.get('part')
            location_id = request.query_params.get('location_id') or request.query_params.get('location')
            
            # Get optional storage location filters
            aisle = request.query_params.get('aisle')
            row = request.query_params.get('row')
            bin_param = request.query_params.get('bin')
            
            # Get base batches from service
            batches = inventory_service.get_batches(
                part_id=part_id,
                location_id=location_id
            )
            
            # Apply additional filtering for aisle, row, bin - if not provided, filter for null values
            if aisle is not None:
                if aisle.strip() == '':
                    batches = batches.filter(aisle__isnull=True)
                else:
                    batches = batches.filter(aisle=aisle)
            else:
                # If aisle not provided, only get records with null aisle
                batches = batches.filter(aisle__isnull=True)
            
            if row is not None:
                if row.strip() == '':
                    batches = batches.filter(row__isnull=True)
                else:
                    batches = batches.filter(row=row)
            else:
                # If row not provided, only get records with null row
                batches = batches.filter(row__isnull=True)
            
            if bin_param is not None:
                if bin_param.strip() == '':
                    batches = batches.filter(bin__isnull=True)
                else:
                    batches = batches.filter(bin=bin_param)
            else:
                # If bin not provided, only get records with null bin
                batches = batches.filter(bin__isnull=True)
            
            # Serialize the batches
            serializer = InventoryBatchBaseSerializer(batches, many=True, context={'request': request})
            
            return self.format_response(serializer.data, None, status.HTTP_200_OK)
            
        except Exception as e:
            return self.handle_exception(e)
    
    def get_work_order_parts(self, request, work_order_id):
        """Get work order parts summary"""
        try:
            data = inventory_service.get_work_order_parts(work_order_id)
            
            # Serialize the parts
            parts_serializer = WorkOrderPartBaseSerializer(data['parts'], many=True, context={'request': request})
            
            return self.format_response(
                {
                    'work_order_id': data['work_order_id'],
                    'parts': parts_serializer.data,
                    'total_parts_cost': str(data['total_parts_cost'])
                },
                None,
                status.HTTP_200_OK
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def get_movements(self, request):
        """Get part movements with optional filtering including inventory_batch positioning"""
        try:
            # Parse query parameters - support both formats
            part_id = request.query_params.get('part_id') or request.query_params.get('part')
            location_id = request.query_params.get('location_id') or request.query_params.get('location')
            work_order_id = request.query_params.get('work_order_id') or request.query_params.get('work_order')
            from_date = request.query_params.get('from_date')
            to_date = request.query_params.get('to_date')
            limit = int(request.query_params.get('limit', 100))
            
            # Extract positioning parameters for inventory_batch filtering
            aisle = request.query_params.get('aisle')
            row = request.query_params.get('row')
            bin_param = request.query_params.get('bin')
            
            # Parse dates if provided
            if from_date:
                from_date = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
            if to_date:
                to_date = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
            
            movements = inventory_service.get_movements(
                part_id=part_id,
                location_id=location_id,
                work_order_id=work_order_id,
                from_date=from_date,
                to_date=to_date,
                limit=limit,
                aisle=aisle,
                row=row,
                bin=bin_param
            )
            
            # Serialize the movements
            serializer = PartMovementBaseSerializer(movements, many=True, context={'request': request})
            
            return self.format_response(serializer.data, None, status.HTTP_200_OK)
            
        except Exception as e:
            return self.handle_exception(e)
    
    def _get_validated_part_locations_data(self, request, allow_both_params=True):
        """
        Common method to validate parameters and get part location data.
        
        Args:
            request: The HTTP request object
            allow_both_params: If True, accepts both 'part_id' and 'part' params.
                              If False, only accepts 'part' param.
        
        Returns:
            List of inventory data dictionaries
        
        Raises:
            LocalBaseException: For validation or data retrieval errors
        """
        # Validate query parameters
        if allow_both_params:
            part_id = request.query_params.get('part_id') or request.query_params.get('part')
            error_msg = "part_id or part parameter is required"
        else:
            part_id = request.query_params.get('part')
            error_msg = "part parameter is required"
            
        if not part_id:
            raise LocalBaseException(
                exception=error_msg,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = LocationOnHandQuerySerializer(data={'part_id': part_id})
        if not serializer.is_valid():
            raise LocalBaseException(
                exception=str(serializer.errors),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        validated_part_id = serializer.validated_data['part_id']
        
        # Use service to get the data
        from parts.services import inventory_service, InventoryError
        
        try:
            inventory_data = inventory_service.get_part_locations_on_hand(validated_part_id)
        except InventoryError as e:
            raise LocalBaseException(
                exception=str(e),
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        return inventory_data
    
    def get_locations_on_hand(self, request):
        """Get all locations with aggregated inventory batch records for a specific part"""
        try:
            # Get validated data using common method (supports both part_id and part params)
            inventory_data = self._get_validated_part_locations_data(request, allow_both_params=True)
            
            # Format the response data
            response_data = []
            
            for item in inventory_data:
                response_data.append({
                    'site': {
                        'id': str(item['location__site__id']) if item['location__site__id'] else None,
                        'code': item['location__site__code'] or '',
                        'name': item['location__site__name'] or ''
                    } if item['location__site__id'] else None,
                    'location': {
                        'id': str(item['location__id']),
                        'name': item['location__name']
                    },
                    'aisle': item['normalized_aisle'] or '',
                    'row': item['normalized_row'] or '',
                    'bin': item['normalized_bin'] or '',
                    'qty_on_hand': str(item['total_qty_on_hand'])
                })
            
            return self.format_response(response_data, None, status.HTTP_200_OK)
            
        except Exception as e:
            return self.handle_exception(e)
    
    def get_part_locations(self, request):
        """Get part locations with simplified name-based response format"""
        try:
            # Get validated data using common method (only accepts 'part' param)
            inventory_data = self._get_validated_part_locations_data(request, allow_both_params=False)
            
            # Format the response data with name entries
            locations = []
            total_qty = 0
            
            for item in inventory_data:
                qty_on_hand = float(item['total_qty_on_hand'])
                total_qty += qty_on_hand
                
                # Format aisle/row/bin with A/R/B prefixes
                aisle = item['normalized_aisle'] or ''
                row = item['normalized_row'] or ''
                bin_val = item['normalized_bin'] or ''
                
                aisle_formatted = f"A{aisle}" if aisle else "A"
                row_formatted = f"R{row}" if row else "R"
                bin_formatted = f"B{bin_val}" if bin_val else "B"
                
                # Get site info
                site_code = item['location__site__code'] or ''
                location_name = item['location__name']
                
                # Create the formatted string: "{site.code} - {location.name} - A{aisle}/R{row}/B{bin} - qty:{qty_on_hand}"
                formatted_string = f"{site_code} - {location_name} - {aisle_formatted}/{row_formatted}/{bin_formatted} - qty: {qty_on_hand}"
                
                # Include both id and name with formatted string
                location_data = {
                    "id": formatted_string,
                    "name": formatted_string
                }
                
                locations.append(location_data)
            
            # Create response with the exact structure requested
            from rest_framework.response import Response
            
            response_data = {
                'data': locations,
                'total_locations': len(locations),
                'total_qty': total_qty,
                'errors': None,
                'status_code': 200
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return self.handle_exception(e)


