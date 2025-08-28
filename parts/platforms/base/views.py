from rest_framework import status, viewsets
from datetime import datetime
from django.core.exceptions import ValidationError
from configurations.base_features.views.base_api_view import BaseAPIView
from configurations.base_features.exceptions.base_exceptions import LocalBaseException
from parts.models import Part, InventoryBatch, WorkOrderPart, WorkOrderPartRequest, PartMovement, WorkOrderPartRequestLog
from parts.platforms.base.serializers import *
from parts.services import inventory_service, workflow_service, InsufficientStockError, InvalidOperationError


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
        """Create WorkOrderPart - simplified version for the split model"""
        try:
            from django.db import transaction
            from work_orders.models import WorkOrder
            
            # WorkOrderPartRequest fields to check for in the payload
            work_order_part_request_fields = {
                'inventory_batch', 'qty_needed', 'qty_used', 
                'unit_cost_snapshot', 'is_approved'
            }
            
            with transaction.atomic():
                # Separate WorkOrderPart fields from WorkOrderPartRequest fields
                work_order_part_data = {}
                work_order_part_request_data = {}
                
                for key, value in data.items():
                    if key in work_order_part_request_fields:
                        work_order_part_request_data[key] = value
                    else:
                        work_order_part_data[key] = value
                
                # Validate required fields for WorkOrderPart
                work_order_id = work_order_part_data.get('work_order')
                if not work_order_id:
                    raise LocalBaseException(
                        exception="work_order field is required",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                part_id = work_order_part_data.get('part')
                if not part_id:
                    raise LocalBaseException(
                        exception="part field is required",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                # Validate that work_order and part exist
                try:
                    work_order = WorkOrder.objects.get(id=work_order_id)
                except WorkOrder.DoesNotExist:
                    raise LocalBaseException(
                        exception="Work order not found",
                        status_code=status.HTTP_404_NOT_FOUND
                    )
                
                try:
                    part = Part.objects.get(id=part_id)
                except Part.DoesNotExist:
                    raise LocalBaseException(
                        exception="Part not found",
                        status_code=status.HTTP_404_NOT_FOUND
                    )
                
                # Check if this combination already exists (due to unique_together constraint)
                existing_work_order_part = WorkOrderPart.objects.filter(
                    work_order=work_order,
                    part=part
                ).first()
                
                if existing_work_order_part:
                    # Raise validation error for duplicate WorkOrderPart
                    raise LocalBaseException(
                        exception=f"WorkOrderPart already exists for Work Order '{work_order.code}' and Part '{part.part_number}'. Duplicate records are not allowed.",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                # Create new WorkOrderPart
                serializer = self.serializer_class(data=work_order_part_data)
                if not serializer.is_valid():
                        raise LocalBaseException(
                        exception=serializer.errors,
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                work_order_part = serializer.save()
                
                # Create WorkOrderPartRequest if there are request fields in the payload
                work_order_part_request = None
                if work_order_part_request_data:
                    # Add the work_order_part reference
                    work_order_part_request_data['work_order_part'] = work_order_part.id
                    
                    # Validate and create WorkOrderPartRequest
                    request_serializer = WorkOrderPartRequestBaseSerializer(data=work_order_part_request_data)
                    if not request_serializer.is_valid():
                        raise LocalBaseException(
                            exception=request_serializer.errors,
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                    work_order_part_request = request_serializer.save()
                
                # Prepare response data
                response_data = {
                    'work_order_part': self.serializer_class(work_order_part).data
                }
                
                if work_order_part_request:
                    response_data['work_order_part_request'] = WorkOrderPartRequestBaseSerializer(work_order_part_request).data
                    response_data['message'] = 'WorkOrderPart and WorkOrderPartRequest created successfully'
                else:
                    response_data['message'] = 'WorkOrderPart created successfully'
                
                if return_instance:
                    return work_order_part, response_data
                
                return self.format_response(data=response_data, status_code=201)
        
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
        """Update WorkOrderPart with enhanced location decoding and FIFO inventory handling"""
        try:
            from django.db import transaction, models
            from parts.services import location_decoder
            from decimal import Decimal
            
            # WorkOrderPartRequest fields to check for in the payload
            work_order_part_request_fields = {
                'inventory_batch', 'qty_needed', 'qty_used', 
                'unit_cost_snapshot', 'is_approved'
            }
            
            with transaction.atomic():
                # Get the existing WorkOrderPart instance
                if not pk:
                    raise LocalBaseException(
                        exception="Primary key is required for update",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                try:
                    work_order_part = WorkOrderPart.objects.select_related(
                        'work_order', 'part'
                    ).get(id=pk)
                except WorkOrderPart.DoesNotExist:
                    raise LocalBaseException(
                        exception="Work order part not found",
                        status_code=status.HTTP_404_NOT_FOUND
                    )
                
                # Handle location decoding and qty_used processing
                location = None
                inventory_batch = None
                qty_difference = 0
                current_total_qty = 0
                new_qty_used = 0
                position_filter = {}
                decoded_position = {}
                use_provided_position = False
                
                # Handle qty_needed for planning purposes (create placeholder WOPR)
                # Allow qty_needed even when qty_used is provided
                planning_record_created = False
                if 'qty_needed' in data and 'qty_used' not in data:
                    try:
                        qty_needed_value = int(data.get('qty_needed'))
                        if qty_needed_value > 0:
                            # Check if a planning record already exists (unapproved records)
                            existing_planning_request = work_order_part.part_requests.filter(
                                is_approved=False  # Planning records are not approved
                            ).first()
                            
                            if existing_planning_request:
                                # Update existing planning record
                                existing_planning_request.qty_needed = qty_needed_value
                                existing_planning_request.save(update_fields=['qty_needed'])
                            else:
                                # Create new planning record
                                from parts.models import WorkOrderPartRequest
                                WorkOrderPartRequest.objects.create(
                                    work_order_part=work_order_part,
                                    qty_needed=qty_needed_value,
                                    # inventory_batch=None (default)
                                    # qty_used=None (default) 
                                    # unit_cost_snapshot=None (default)
                                    # is_approved=False (default)
                                )
                            planning_record_created = True
                    except (ValueError, TypeError):
                        raise LocalBaseException(
                            exception="qty_needed must be a valid integer",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )

                # Handle qty_used with or without location
                if 'qty_used' in data:
                    # If location is not provided, try to extract from existing WorkOrderPartRequest
                    if 'location' not in data:
                        existing_requests = work_order_part.part_requests.filter(is_approved=True)
                        if not existing_requests.exists():
                            raise LocalBaseException(
                                exception="qty_used provided without location. No existing WorkOrderPartRequest records found to extract location from. Please provide location parameter.",
                                status_code=status.HTTP_400_BAD_REQUEST
                            )
                        
                        # Check the unique constraint with sum of qty_used consideration
                        current_total_qty = existing_requests.aggregate(
                            total=models.Sum('qty_used')
                        )['total'] or 0
                        
                        # If current sum is 0, we can use any location, otherwise use existing location
                        if current_total_qty == 0:
                            # Can use any location - but still need one from existing records for consistency
                            most_recent_request = existing_requests.order_by('-created_at').first()
                            location = most_recent_request.inventory_batch.location if most_recent_request.inventory_batch else None
                            if not location:
                                raise LocalBaseException(
                                    exception="No valid location found in existing WorkOrderPartRequest records",
                                    status_code=status.HTTP_400_BAD_REQUEST
                                )
                        else:
                            # Must use the same location/positioning due to unique constraint
                            # Find the location from existing records
                            location_request = existing_requests.filter(inventory_batch__isnull=False).first()
                            if not location_request or not location_request.inventory_batch:
                                raise LocalBaseException(
                                    exception="No valid location found in existing WorkOrderPartRequest records with inventory batch",
                                    status_code=status.HTTP_400_BAD_REQUEST
                                )
                            location = location_request.inventory_batch.location
                    else:
                        # Location provided, decode it as before
                        location_value = data['location']
                        try:
                            # Check if it's a UUID or location string
                            import uuid
                            try:
                                uuid.UUID(location_value)
                                # It's a UUID, get location directly
                                from company.models import Location
                                location = Location.objects.select_related('site').get(id=location_value)
                            except (ValueError, AttributeError):
                                # It's a location string, decode it
                                decoded = location_decoder.decode_location_string(location_value)
                                location = location_decoder.get_location_by_site_and_name(
                                    decoded['site_code'], decoded['location_name']
                                )
                                if not location:
                                    raise LocalBaseException(
                                        exception=f"Location not found: {decoded['site_code']} - {decoded['location_name']}",
                                        status_code=status.HTTP_404_NOT_FOUND
                                    )
                                
                                # Store decoded position information for later use
                                decoded_position = {
                                    'aisle': decoded.get('aisle'),
                                    'row': decoded.get('row'),
                                    'bin': decoded.get('bin')
                                }
                        except Exception as e:
                            raise LocalBaseException(
                                exception=f"Invalid location format: {str(e)}",
                                status_code=status.HTTP_400_BAD_REQUEST
                            )
                    
                    # Calculate current total qty_used (recalculate for accuracy)
                    current_total_qty = work_order_part.part_requests.aggregate(
                        total=models.Sum('qty_used')
                    )['total'] or 0
                    
                    # Get new qty_used from request
                    try:
                        new_qty_used = int(data['qty_used'])
                        if new_qty_used < 0:
                            raise LocalBaseException(
                                exception="qty_used cannot be negative",
                                status_code=status.HTTP_400_BAD_REQUEST
                            )
                    except (ValueError, TypeError):
                        raise LocalBaseException(
                            exception="qty_used must be a valid integer",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                    
                                    # Determine if it's addition or return
                qty_difference = new_qty_used - current_total_qty
                
                # Store qty_difference for later use in response
                
                if qty_difference > 0:
                    # Addition - need to allocate more inventory using FIFO
                    position_filter = {}  # Reset for this operation
                    all_requests = work_order_part.part_requests.all()
                    
                    # Calculate sum of qty_used from all existing records
                    existing_qty_sum = all_requests.aggregate(
                        total=models.Sum('qty_used')
                    )['total'] or 0
                    
                    # Get position constraints based on business rules
                    constraint_aisle = None
                    constraint_row = None
                    constraint_bin = None
                    
                    if existing_qty_sum == 0:
                        # No existing records OR sum of qty_used = 0: Use provided location and position
                        use_provided_position = True
                        
                        # Check if position information was provided via location string decoding
                        if decoded_position and any(decoded_position.values()):
                            # Position info was provided, use it for position-specific FIFO
                            constraint_aisle = decoded_position.get('aisle')
                            constraint_row = decoded_position.get('row')
                            constraint_bin = decoded_position.get('bin')
                            
                            # Store for response data
                            position_filter = {
                                'aisle': constraint_aisle,
                                'row': constraint_row,
                                'bin': constraint_bin
                            }
                        else:
                            # No position info provided, use location-wide FIFO
                            # constraint_aisle, constraint_row, constraint_bin remain None
                            pass
                        
                    else:
                        # Existing records with sum > 0: Must validate against existing position
                        existing_requests = all_requests.filter(is_approved=True)
                        if existing_requests.exists():
                            first_request = existing_requests.first()
                            if first_request.inventory_batch:
                                # Get existing position
                                existing_aisle = first_request.inventory_batch.aisle
                                existing_row = first_request.inventory_batch.row
                                existing_bin = first_request.inventory_batch.bin
                                existing_location = first_request.inventory_batch.location
                                
                                # Check if provided location matches existing location
                                if location.id != existing_location.id:
                                    existing_pos = f"A{existing_aisle or ''}/R{existing_row or ''}/B{existing_bin or ''}"
                                    provided_pos = f"location {location.name}"
                                    raise LocalBaseException(
                                        exception=f"Cannot add parts from different location. Existing parts are from {existing_location.name} at {existing_pos}, but trying to add from {provided_pos}",
                                        status_code=status.HTTP_400_BAD_REQUEST
                                    )
                                
                                # Location matches, now check if provided position matches existing position
                                # Check if position was provided and differs from existing
                                if decoded_position and any(decoded_position.values()):
                                    provided_aisle = decoded_position.get('aisle')
                                    provided_row = decoded_position.get('row') 
                                    provided_bin = decoded_position.get('bin')
                                    
                                    # Compare provided position with existing position
                                    position_match = (
                                        provided_aisle == existing_aisle and
                                        provided_row == existing_row and
                                        provided_bin == existing_bin
                                    )
                                    
                                    if not position_match:
                                        existing_pos = f"A{existing_aisle or ''}/R{existing_row or ''}/B{existing_bin or ''}"
                                        provided_pos = f"A{provided_aisle or ''}/R{provided_row or ''}/B{provided_bin or ''}"
                                        raise LocalBaseException(
                                            exception=f"Cannot add parts from different position. Existing parts are at {existing_location.name} {existing_pos}, but trying to add from {location.name} {provided_pos}",
                                            status_code=status.HTTP_400_BAD_REQUEST
                                        )
                                
                                # Use existing position for constraints
                                constraint_aisle = existing_aisle
                                constraint_row = existing_row
                                constraint_bin = existing_bin
                                
                                # Store for response data
                                position_filter = {
                                    'aisle': constraint_aisle,
                                    'row': constraint_row,
                                    'bin': constraint_bin
                                }
                    
                    # Build base queryset
                    available_batches_query = InventoryBatch.objects.filter(
                        part=work_order_part.part,
                        location=location,
                        qty_on_hand__gt=0
                    )
                    
                    # Apply position filters using same methodology as transfer logic
                    if constraint_aisle is not None:
                        if constraint_aisle == '':
                            available_batches_query = available_batches_query.filter(aisle__isnull=True)
                        else:
                            available_batches_query = available_batches_query.filter(aisle=constraint_aisle)
                    
                    if constraint_row is not None:
                        if constraint_row == '':
                            available_batches_query = available_batches_query.filter(row__isnull=True)
                        else:
                            available_batches_query = available_batches_query.filter(row=constraint_row)
                    
                    if constraint_bin is not None:
                        if constraint_bin == '':
                            available_batches_query = available_batches_query.filter(bin__isnull=True)
                        else:
                            available_batches_query = available_batches_query.filter(bin=constraint_bin)
                    
                    available_batches = available_batches_query.order_by('received_date')  # FIFO
                    
                    # Create position description for error messages
                    position_desc = ""
                    if constraint_aisle is not None or constraint_row is not None or constraint_bin is not None:
                        aisle = constraint_aisle or ''
                        row = constraint_row or ''
                        bin_val = constraint_bin or ''
                        position_desc = f" at position A{aisle}/R{row}/B{bin_val}"
                    
                    if not available_batches.exists():
                        raise LocalBaseException(
                            exception=f"No inventory available for part {work_order_part.part.part_number} at location {location.name}{position_desc}",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                    
                    # Check if we have enough total inventory at this specific position
                    total_available = sum(batch.qty_on_hand for batch in available_batches)
                    if total_available < qty_difference:
                        raise LocalBaseException(
                            exception=f"Insufficient inventory at location {location.name}{position_desc}. Requested: {qty_difference}, Available: {total_available}",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                    
                    # Use FIFO allocation across batches
                    remaining_qty = qty_difference
                    for batch in available_batches:
                        if remaining_qty <= 0:
                            break
                            
                        qty_from_batch = min(remaining_qty, batch.qty_on_hand)
                        
                        # Update inventory - reduce qty_on_hand
                        batch.qty_on_hand -= qty_from_batch
                        batch.save(update_fields=['qty_on_hand'])
                        
                        # Create movement record for audit trail
                        PartMovement.objects.create(
                            part=work_order_part.part,
                            inventory_batch=batch,
                            from_location=location,
                            to_location=None,  # Parts are consumed
                            movement_type=PartMovement.MovementType.ISSUE,
                            qty_delta=-qty_from_batch,
                            work_order=work_order_part.work_order,
                            created_by=params.get('user')
                        )
                        
                        # Create/update WorkOrderPartRequest for this batch
                        existing_request = work_order_part.part_requests.filter(
                            inventory_batch=batch
                        ).first()
                        
                        if existing_request:
                            # Update existing request
                            existing_request.qty_used += qty_from_batch
                            existing_request.total_parts_cost = existing_request.qty_used * existing_request.unit_cost_snapshot
                            
                            # Update qty_needed if provided (for combined planning + consumption)
                            update_fields = ['qty_used', 'total_parts_cost']
                            if 'qty_needed' in data:
                                try:
                                    qty_needed_value = int(data.get('qty_needed'))
                                    if qty_needed_value > 0:
                                        existing_request.qty_needed = qty_needed_value
                                        update_fields.append('qty_needed')
                                except (ValueError, TypeError):
                                    pass  # Skip invalid qty_needed
                            
                            existing_request.save(update_fields=update_fields)
                        else:
                            # Create new request for this batch
                            from parts.models import WorkOrderPartRequest
                            # Include qty_needed if provided along with qty_used
                            create_data = {
                                'work_order_part': work_order_part,
                                'inventory_batch': batch,
                                'qty_used': qty_from_batch,
                                'unit_cost_snapshot': batch.last_unit_cost
                            }
                            
                            # Add qty_needed if provided (for combined planning + consumption)
                            if 'qty_needed' in data:
                                try:
                                    qty_needed_value = int(data.get('qty_needed'))
                                    if qty_needed_value > 0:
                                        create_data['qty_needed'] = qty_needed_value
                                except (ValueError, TypeError):
                                    pass  # Skip invalid qty_needed
                            
                            WorkOrderPartRequest.objects.create(**create_data)
                        
                        remaining_qty -= qty_from_batch
                    
                    # Use first batch for consistency with existing logic
                    inventory_batch = available_batches.first()
                    
                elif qty_difference < 0:
                    # Return - need to return parts back to inventory using LIFO
                    position_filter = {}  # Reset for this operation
                    qty_to_return = abs(qty_difference)
                    
                    # Get WorkOrderPartRequest records ordered by most recent (LIFO for returns)
                    request_records = work_order_part.part_requests.filter(is_approved=True).order_by('-created_at')
                    
                    if not request_records.exists():
                        raise LocalBaseException(
                            exception="No parts to return for this work order part",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                    
                    # Return parts using LIFO (most recent first)
                    remaining_return_qty = qty_to_return
                    inventory_batch = None  # Will be set to last processed batch
                    
                    for request in request_records:
                        if remaining_return_qty <= 0:
                            break
                            
                        # Determine how much to return from this request
                        return_from_request = min(remaining_return_qty, request.qty_used)
                        
                        # Update inventory - add back to qty_on_hand
                        request.inventory_batch.qty_on_hand += return_from_request
                        request.inventory_batch.save(update_fields=['qty_on_hand'])
                        
                        # Create movement record for audit trail
                        PartMovement.objects.create(
                            part=work_order_part.part,
                            inventory_batch=request.inventory_batch,
                            from_location=None,  # Parts are being returned
                            to_location=request.inventory_batch.location,
                            movement_type=PartMovement.MovementType.RETURN,
                            qty_delta=return_from_request,
                            work_order=work_order_part.work_order,
                            created_by=params.get('user')
                        )
                        
                        # Update the WOPR record
                        request.qty_used -= return_from_request
                        request.total_parts_cost = request.qty_used * request.unit_cost_snapshot
                        
                        if request.qty_used <= 0:
                            # Delete the request if qty_used becomes 0 or negative
                            inventory_batch = request.inventory_batch  # Save reference before deletion
                            request.delete()
                        else:
                            # Update the request with reduced qty_used
                            request.save(update_fields=['qty_used', 'total_parts_cost'])
                            inventory_batch = request.inventory_batch
                        
                        remaining_return_qty -= return_from_request
                    
                    if remaining_return_qty > 0:
                        raise LocalBaseException(
                            exception=f"Cannot return {remaining_return_qty} units - insufficient qty_used in requests",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                        
                else:
                    # No change in qty_used, just use any existing inventory batch
                    position_filter = {}  # Reset for this operation
                    existing_request = work_order_part.part_requests.filter(is_approved=True).first()
                    inventory_batch = existing_request.inventory_batch if existing_request else None
                
                # Separate WorkOrderPart fields from WorkOrderPartRequest fields
                work_order_part_data = {}
                work_order_part_request_data = {}
                
                for key, value in data.items():
                    if key in work_order_part_request_fields:
                        work_order_part_request_data[key] = value
                    elif key not in ['location']:  # Exclude location from WorkOrderPart data
                        work_order_part_data[key] = value
                
                # Update WorkOrderPart if there are valid fields to update
                if work_order_part_data:
                    serializer = self.serializer_class(work_order_part, data=work_order_part_data, partial=True)
                    if not serializer.is_valid():
                        raise LocalBaseException(
                            exception=serializer.errors,
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                    work_order_part = serializer.save()
                
                # Note: WorkOrderPartRequest records are now handled within the qty_used logic above
                # No need to create additional records here since we update/create them properly in FIFO/LIFO logic
                work_order_part_request = None
                qty_difference = locals().get('qty_difference', 0)  # Get qty_difference if it was calculated
                
                # Prepare response data
                response_data = {
                    'work_order_part': self.serializer_class(work_order_part).data
                }
                
                # Add inventory operation details if qty_used was processed
                if 'qty_used' in data and location:
                    inventory_operation = {
                        'location': {
                            'id': str(location.id),
                            'name': location.name
                        },
                        'inventory_batch': {
                            'id': str(inventory_batch.id),
                            'received_date': inventory_batch.received_date.isoformat(),
                            'aisle': inventory_batch.aisle or '',
                            'row': inventory_batch.row or '',
                            'bin': inventory_batch.bin or ''
                        } if inventory_batch else None,
                        'operation_type': 'addition' if qty_difference > 0 else 'return' if qty_difference < 0 else 'no_change',
                        'qty_difference': qty_difference,
                        'new_total_qty_used': new_qty_used,
                        'previous_total_qty_used': current_total_qty
                    }
                    
                    # Add position-specific information if available
                    if inventory_batch:
                        aisle = inventory_batch.aisle or ''
                        row = inventory_batch.row or ''
                        bin_val = inventory_batch.bin or ''
                        inventory_operation['position'] = f"A{aisle}/R{row}/B{bin_val}"
                        inventory_operation['fifo_applied_to_position'] = bool(position_filter)
                        inventory_operation['position_source'] = 'provided' if use_provided_position and position_filter else 'existing' if position_filter else 'location_wide'
                    
                    response_data['inventory_operation'] = inventory_operation
                
                # Get updated part requests for response
                updated_requests = work_order_part.part_requests.all()
                if updated_requests.exists():
                    response_data['work_order_part_requests'] = WorkOrderPartRequestBaseSerializer(updated_requests, many=True).data
                
                # Set appropriate message based on operation
                if 'qty_used' in data:
                    if qty_difference > 0:
                        position_msg = ""
                        if position_filter:
                            aisle = position_filter.get('aisle') or ''
                            row = position_filter.get('row') or ''
                            bin_val = position_filter.get('bin') or ''
                            if use_provided_position:
                                position_msg = f" using provided position-specific FIFO at A{aisle}/R{row}/B{bin_val}"
                            else:
                                position_msg = f" using existing position-specific FIFO at A{aisle}/R{row}/B{bin_val}"
                        else:
                            position_msg = " using location-wide FIFO"
                        base_msg = f'WorkOrderPart updated successfully. Added {qty_difference} parts to inventory consumption{position_msg}.'
                        if 'qty_needed' in data:
                            try:
                                qty_needed_value = int(data.get('qty_needed'))
                                base_msg += f' Planning qty_needed: {qty_needed_value} included in consumption records.'
                            except (ValueError, TypeError):
                                pass
                        response_data['message'] = base_msg
                    elif qty_difference < 0:
                        base_msg = f'WorkOrderPart updated successfully. Returned {abs(qty_difference)} parts to inventory using LIFO.'
                        if 'qty_needed' in data:
                            try:
                                qty_needed_value = int(data.get('qty_needed'))
                                base_msg += f' Planning qty_needed: {qty_needed_value} noted.'
                            except (ValueError, TypeError):
                                pass
                        response_data['message'] = base_msg
                    else:
                        base_msg = 'WorkOrderPart updated successfully. No quantity change.'
                        if 'qty_needed' in data:
                            try:
                                qty_needed_value = int(data.get('qty_needed'))
                                base_msg += f' Planning qty_needed: {qty_needed_value} noted.'
                            except (ValueError, TypeError):
                                pass
                        response_data['message'] = base_msg
                elif planning_record_created:
                    try:
                        qty_needed_value = int(data.get('qty_needed', 0))
                        response_data['message'] = f'WorkOrderPart updated successfully. Planning record created/updated with qty_needed: {qty_needed_value}.'
                    except (ValueError, TypeError):
                        response_data['message'] = 'WorkOrderPart updated successfully. Planning record created/updated.'
                else:
                    response_data['message'] = 'WorkOrderPart updated successfully'
                
                return self.format_response(data=response_data, status_code=200)
        
        except Exception as e:
            return self.handle_exception(e)
    

class WorkOrderPartRequestBaseView(BaseAPIView):
    """Base view for WorkOrderPartRequest CRUD operations"""
    serializer_class = WorkOrderPartRequestBaseSerializer
    model_class = WorkOrderPartRequest


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
        
        # Get optional site or work_order parameter
        site_id = request.query_params.get('site')
        work_order_id = request.query_params.get('work_order')
        
        # If work_order is provided, extract site from work_order.asset.location.site
        if work_order_id:
            try:
                from work_orders.models import WorkOrder
                from configurations.base_features.db.db_helpers import get_object_by_content_type_and_id
                
                work_order = WorkOrder.objects.select_related('content_type').get(id=work_order_id)
                
                # Get the asset using the utility function
                if not work_order.content_type or not work_order.object_id:
                    raise LocalBaseException(
                        exception="Work order does not have a valid asset reference",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                try:
                    asset = get_object_by_content_type_and_id(work_order.content_type.id, work_order.object_id)
                except Exception:
                    raise LocalBaseException(
                        exception="Work order asset not found",
                        status_code=status.HTTP_404_NOT_FOUND
                    )
                
                # Get location from asset
                if not hasattr(asset, 'location') or not asset.location:
                    raise LocalBaseException(
                        exception="Work order asset does not have a valid location",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                # Get site from location
                location = asset.location
                if not hasattr(location, 'site') or not location.site:
                    raise LocalBaseException(
                        exception="Asset location does not have a valid site",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                # Override site_id with the one from work order
                site_id = str(location.site.id)
                
                # Check if inventory batches exist for this part and site when work_order is provided
                from parts.models import InventoryBatch, Part
                inventory_exists = InventoryBatch.objects.filter(
                    part_id=part_id,
                    location__site_id=site_id
                ).exists()
                
                if not inventory_exists:
                    # Get part number for better error message
                    try:
                        part = Part.objects.get(id=part_id)
                        part_identifier = part.part_number
                    except Part.DoesNotExist:
                        part_identifier = part_id
                    
                    raise LocalBaseException(
                        exception=f"No inventory locations found for part {part_identifier} at site {location.site.code or site_id}",
                        status_code=status.HTTP_404_NOT_FOUND
                    )
                
            except WorkOrder.DoesNotExist:
                raise LocalBaseException(
                    exception=f"Work order with ID {work_order_id} does not exist",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                if isinstance(e, LocalBaseException):
                    raise e
                raise LocalBaseException(
                    exception=f"Error processing work order: {str(e)}",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        
        # Validate site if provided directly or extracted from work order
        if site_id:
            try:
                from company.models import Site
                Site.objects.get(id=site_id)  # Validate site exists
            except Site.DoesNotExist:
                raise LocalBaseException(
                    exception=f"Site with ID {site_id} does not exist",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            except Exception:
                raise LocalBaseException(
                    exception="Invalid site ID format",
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
            inventory_data = inventory_service.get_part_locations_on_hand(validated_part_id, site_id)
        except InventoryError as e:
            raise LocalBaseException(
                exception=str(e),
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        return inventory_data
    
    def get_locations_on_hand(self, request):
        """Get all locations with aggregated inventory batch records for a specific part
        
        Query Parameters:
            part_id or part (required): Part ID to get locations for
            site (optional): Site ID to filter locations by site
            work_order (optional): Work Order ID - extracts site from work_order.asset.location.site
        """
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
        """Get part locations with simplified name-based response format
        
        Query Parameters:
            part (required): Part ID to get locations for
            site (optional): Site ID to filter locations by site
            work_order (optional): Work Order ID - extracts site from work_order.asset.location.site
        """
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
            
            return self.format_response(locations, [], 200)
            
        except Exception as e:
            return self.handle_exception(e)


class WorkOrderPartMovementBaseView(PartMovementBaseView):
    """Base view for WorkOrderPart movement logs - filtered for work order related movements only"""
    serializer_class = WorkOrderPartMovementSerializer
    model_class = PartMovement
    
    def get_request_params(self, request):
        """Override to add work order filter to params"""
        params = super().get_request_params(request)
        # Filter to only show movements that are related to work orders
        params['work_order__isnull'] = False
        return params


class WorkOrderPartRequestWorkflowBaseView(BaseAPIView, viewsets.ViewSet):
    """Base view for WOPR workflow operations"""
    model_class = WorkOrderPartRequest
    http_method_names = ['get', 'post']
    
    def _get_client_metadata(self, request):
        """Extract client metadata for audit logging"""
        return {
            'ip_address': request.META.get('REMOTE_ADDR'),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500]  # Truncate long user agents
        }
    
    def request_parts(self, request, pk=None):
        """
        POST /work-order-parts/{id}/request
        Mechanic requests parts for a WorkOrderPart
        """
        try:
            serializer = RequestPartsSerializer(data=request.data)
            if not serializer.is_valid():
                return self.format_response(
                    data=None,
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get client metadata
            metadata = self._get_client_metadata(request)
            
            # Call service with WorkOrderPart ID
            result = workflow_service.request_parts_for_work_order_part(
                wop_id=pk,
                qty_needed=serializer.validated_data['qty_needed'],
                performed_by=request.user,
                notes=serializer.validated_data.get('notes'),
                **metadata
            )
            
            return self.format_response(
                data=result,
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def confirm_availability(self, request, pk=None):
        """
        POST /work-order-part-requests/{id}/confirm-availability
        Warehouse keeper confirms availability and reserves parts
        """
        try:
            serializer = ConfirmAvailabilitySerializer(data=request.data)
            if not serializer.is_valid():
                return self.format_response(
                    data=None,
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get client metadata
            metadata = self._get_client_metadata(request)
            
            # Call service
            result = workflow_service.confirm_availability(
                wopr_id=pk,
                qty_available=serializer.validated_data['qty_available'],
                inventory_batch_id=str(serializer.validated_data['inventory_batch_id']),
                performed_by=request.user,
                notes=serializer.validated_data.get('notes'),
                **metadata
            )
            
            return self.format_response(
                data=result,
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def mark_ordered(self, request, pk=None):
        """
        POST /work-order-part-requests/{id}/mark-ordered
        Mark parts as ordered externally
        """
        try:
            serializer = MarkOrderedSerializer(data=request.data)
            if not serializer.is_valid():
                return self.format_response(
                    data=None,
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get client metadata
            metadata = self._get_client_metadata(request)
            
            # Call service
            result = workflow_service.mark_ordered(
                wopr_id=pk,
                performed_by=request.user,
                notes=serializer.validated_data.get('notes'),
                **metadata
            )
            
            return self.format_response(
                data=result,
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def deliver_parts(self, request, pk=None):
        """
        POST /work-order-part-requests/{id}/deliver
        Warehouse keeper delivers parts (marks ready for pickup)
        """
        try:
            serializer = DeliverPartsSerializer(data=request.data)
            if not serializer.is_valid():
                return self.format_response(
                    data=None,
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get client metadata
            metadata = self._get_client_metadata(request)
            
            # Call service
            result = workflow_service.deliver_parts(
                wopr_id=pk,
                qty_delivered=serializer.validated_data['qty_delivered'],
                performed_by=request.user,
                notes=serializer.validated_data.get('notes'),
                **metadata
            )
            
            return self.format_response(
                data=result,
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def pickup_parts(self, request, pk=None):
        """
        POST /work-order-part-requests/{id}/pickup
        Mechanic picks up parts (confirms receipt)
        """
        try:
            serializer = PickupPartsSerializer(data=request.data)
            if not serializer.is_valid():
                return self.format_response(
                    data=None,
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get client metadata
            metadata = self._get_client_metadata(request)
            
            # Call service
            result = workflow_service.pickup_parts(
                wopr_id=pk,
                qty_picked_up=serializer.validated_data['qty_picked_up'],
                performed_by=request.user,
                notes=serializer.validated_data.get('notes'),
                **metadata
            )
            
            return self.format_response(
                data=result,
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def cancel_availability(self, request, pk=None):
        """
        POST /work-order-part-requests/{id}/cancel-availability
        Cancel parts availability and release reservation
        """
        try:
            serializer = CancelAvailabilitySerializer(data=request.data)
            if not serializer.is_valid():
                return self.format_response(
                    data=None,
                    errors=serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Get client metadata
            metadata = self._get_client_metadata(request)
            
            # Call service
            result = workflow_service.cancel_availability(
                wopr_id=pk,
                performed_by=request.user,
                notes=serializer.validated_data.get('notes'),
                **metadata
            )
            
            return self.format_response(
                data=result,
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def pending_requests(self, request):
        """
        GET /work-order-part-requests/pending
        Get all pending part requests for warehouse keepers
        """
        try:
            # Get query parameters for filtering
            work_order_id = request.query_params.get('work_order_id')
            part_id = request.query_params.get('part_id')
            location_id = request.query_params.get('location_id')
            limit = int(request.query_params.get('limit', 100))
            offset = int(request.query_params.get('offset', 0))
            
            # Base queryset for pending requests
            queryset = WorkOrderPartRequest.objects.filter(
                is_requested=True,
                is_available=False  # Not yet processed by warehouse
            ).select_related(
                'work_order_part__work_order',
                'work_order_part__work_order__content_type',
                'work_order_part__part',
                'inventory_batch__location'
            ).prefetch_related(
                'audit_logs'
            )
            
            # Apply filters
            if work_order_id:
                queryset = queryset.filter(work_order_part__work_order_id=work_order_id)
            if part_id:
                queryset = queryset.filter(work_order_part__part_id=part_id)
            if location_id:
                # Filter by parts that have inventory in the specified location
                queryset = queryset.filter(
                    work_order_part__part__inventory_batches__location_id=location_id,
                    work_order_part__part__inventory_batches__qty_on_hand__gt=0
                ).distinct()
            
            # Order by priority (most recent first, then by work order priority if available)
            queryset = queryset.order_by('-created_at')
            
            # Apply pagination
            total_count = queryset.count()
            queryset = queryset[offset:offset + limit]
            
            # Serialize the data
            serialized_data = []
            for wopr in queryset:
                # Get available inventory for this part
                available_inventory = []
                for batch in wopr.work_order_part.part.inventory_batches.filter(qty_on_hand__gt=0):
                    available_qty = batch.qty_on_hand - batch.qty_reserved
                    if available_qty > 0:
                        available_inventory.append({
                            'inventory_batch_id': str(batch.id),
                            'location': str(batch.location),
                            'location_id': str(batch.location.id),
                            'available_qty': available_qty,
                            'unit_cost': str(batch.last_unit_cost),
                            'aisle': batch.aisle,
                            'row': batch.row,
                            'bin': batch.bin,
                            'received_date': batch.received_date.isoformat()
                        })
                
                # Get request timeline
                first_requested = wopr.get_first_requested_at()
                
                # Format asset information using GenericForeignKey
                work_order = wopr.work_order_part.work_order
                asset_display = None
                asset_location_display = None
                
                # Get the asset using the GenericForeignKey approach
                if work_order.content_type and work_order.object_id:
                    try:
                        from configurations.base_features.db.db_helpers import get_object_by_content_type_and_id
                        asset = get_object_by_content_type_and_id(work_order.content_type.id, work_order.object_id)
                        
                        if asset:
                            # Format: "(asset_code) asset_name" e.g. "(T01) JLG Telehandler"
                            asset_code = getattr(asset, 'code', '') or getattr(asset, 'asset_code', '') or ''
                            asset_name = getattr(asset, 'name', '') or getattr(asset, 'asset_name', '') or ''
                            if asset_code and asset_name:
                                asset_display = f"({asset_code}) {asset_name}"
                            elif asset_name:
                                asset_display = asset_name
                            elif asset_code:
                                asset_display = f"({asset_code})"
                            
                            # Format asset location: "site_code - location_name" e.g. "RC - MOUNTAIN"
                            if hasattr(asset, 'location') and asset.location:
                                location = asset.location
                                site_code = location.site.code if hasattr(location, 'site') and location.site else ''
                                location_name = location.name if location else ''
                                if site_code and location_name:
                                    asset_location_display = f"{site_code} - {location_name}"
                                elif location_name:
                                    asset_location_display = location_name
                                elif site_code:
                                    asset_location_display = site_code
                    except Exception:
                        # If asset retrieval fails, continue without asset info
                        pass
                
                item_data = {
                    'id': str(wopr.id),
                    'work_order_code': wopr.work_order_part.work_order.code,
                    'work_order_id': str(wopr.work_order_part.work_order.id),
                    'asset': asset_display,
                    'asset_location': asset_location_display,
                    'part_number': wopr.work_order_part.part.part_number,
                    'part_name': wopr.work_order_part.part.name,
                    'part_id': str(wopr.work_order_part.part.id),
                    'qty_needed': wopr.qty_needed,
                    'qty_available': wopr.qty_available,
                    'qty_delivered': wopr.qty_delivered,
                    'is_requested': wopr.is_requested,
                    'is_available': wopr.is_available,
                    'is_ordered': wopr.is_ordered,
                    'is_delivered': wopr.is_delivered,
                    'requested_at': first_requested.isoformat() if first_requested else None,
                    'created_at': wopr.created_at.isoformat(),
                    'available_inventory': available_inventory,
                    'total_available_qty': sum(inv['available_qty'] for inv in available_inventory),
                    'can_fulfill': sum(inv['available_qty'] for inv in available_inventory) >= (wopr.qty_needed or 0)
                }
                serialized_data.append(item_data)
            
            return self.format_response(
                data={
                    'results': serialized_data,
                    'count': len(serialized_data),
                    'total_count': total_count,
                    'has_more': (offset + limit) < total_count,
                    'next_offset': offset + limit if (offset + limit) < total_count else None
                },
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return self.handle_exception(e)


class WorkOrderPartRequestLogBaseView(BaseAPIView):
    """Base view for WorkOrderPartRequestLog CRUD operations"""
    serializer_class = WorkOrderPartRequestLogBaseSerializer
    model_class = WorkOrderPartRequestLog
    http_method_names = ['get']  # Read-only
    
    def get_request_params(self, request):
        """Override to add workflow-specific filtering"""
        params = super().get_request_params(request)
        
        # Add filtering by work order part request
        wopr_id = request.query_params.get('work_order_part_request_id')
        if wopr_id:
            params['work_order_part_request'] = wopr_id
        
        # Add filtering by action type
        action_type = request.query_params.get('action_type')
        if action_type:
            params['action_type'] = action_type
        
        # Add filtering by user
        performed_by = request.query_params.get('performed_by')
        if performed_by:
            params['performed_by'] = performed_by
        
        return params


