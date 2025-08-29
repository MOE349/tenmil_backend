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
    
    def update(self, data, params, pk=None, *args, **kwargs):
        """Update WorkOrderPart - Direct parts management without workflow flags"""
        try:
            from django.db import transaction, models
            from parts.services import InventoryService
            from parts.models import WorkOrderPart, WorkOrderPartRequest, InventoryBatch, PartMovement
            from company.models import Location
            
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
                
                # Determine operation type
                has_qty_needed = 'qty_needed' in data
                has_qty_used = 'qty_used' in data
                has_location = 'location' in data
                
                # Validate input combinations
                if has_qty_needed and has_qty_used:
                    raise LocalBaseException(
                        exception="Cannot provide both qty_needed and qty_used in the same request",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                

                
                if not has_qty_needed and not has_qty_used:
                    raise LocalBaseException(
                        exception="Either qty_needed or qty_used must be provided",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                
                response_data = {'work_order_part': self.serializer_class(work_order_part).data}
                
                # Scenario 1: Planning record (qty_needed only)
                if has_qty_needed:
                    qty_needed_value = self._validate_quantity(data.get('qty_needed'), 'qty_needed')
                    
                    # Check if WOP has any active workflow flags before allowing qty_needed updates
                    if work_order_part.has_active_workflow_flags():
                        return self.error_response(
                            "Cannot update qty_needed when work order part has active workflow flags (is_requested, is_available, or is_ordered = True)",
                            status_code=400
                        )
                    
                    # Find existing planning record or create new one
                    # Planning records have no inventory_batch and no qty_used
                    existing_planning_record = WorkOrderPartRequest.objects.filter(
                        work_order_part=work_order_part,
                        inventory_batch__isnull=True,  # Planning record (no specific batch)
                        qty_used__isnull=True,        # Not yet consumed
                        is_delivered=False,           # Not yet delivered
                        is_requested=False,           # Not yet requested
                    ).first()
                    
                    if existing_planning_record:
                        # Update existing planning record
                        existing_planning_record.qty_needed = qty_needed_value
                        existing_planning_record.save(update_fields=['qty_needed'])
                        wopr = existing_planning_record
                        operation_message = f'Planning record updated with qty_needed: {qty_needed_value}'
                    else:
                        # Create new WOPR record for planning
                        wopr = WorkOrderPartRequest.objects.create(
                            work_order_part=work_order_part,
                            qty_needed=qty_needed_value,
                            # All workflow flags remain False (default)
                            # No inventory_batch assigned yet
                        )
                        operation_message = f'Planning record created with qty_needed: {qty_needed_value}'
                    
                    response_data.update({
                        'operation_type': 'planning',
                        'message': operation_message,
                        'wopr_record': {
                            'id': str(wopr.id),
                            'qty_needed': wopr.qty_needed,
                            'workflow_flags': {
                                'is_requested': wopr.is_requested,
                                'is_available': wopr.is_available,
                                'is_ordered': wopr.is_ordered,
                                'is_delivered': wopr.is_delivered,
                            }
                        }
                    })
                
                # Scenario 2: Direct consumption/return (qty_used + location)
                elif has_qty_used:
                    qty_used_value = self._validate_quantity(data.get('qty_used'), 'qty_used')
                    location_value = data.get('location')
                    
                    # Calculate current total qty_used for this WOP
                    current_total_used = work_order_part.part_requests.aggregate(
                        total=models.Sum('qty_used')
                    )['total'] or 0
                    
                    # Validate location requirement based on operation type
                    if not has_location and qty_used_value > current_total_used:
                        # This is an addition (consumption) - location is required
                        raise LocalBaseException(
                            exception="location field is required when adding qty_used (consumption operation)",
                            status_code=status.HTTP_400_BAD_REQUEST
                        )
                    
                    # Only decode location if it's provided (needed for consumption, optional for returns)
                    if has_location:
                        # Decode location using existing service
                        try:
                            site_code, location_name, aisle, row, bin_code = InventoryService.decode_location(location_value)
                        except Exception as e:
                            raise LocalBaseException(
                                exception=f"Invalid location format: {str(e)}",
                                status_code=status.HTTP_400_BAD_REQUEST
                            )
                        
                        # Get location object
                        try:
                            location = Location.objects.select_related('site').get(
                                site__code=site_code,
                                name=location_name
                            )
                        except Location.DoesNotExist:
                            raise LocalBaseException(
                                exception=f"Location not found for site code '{site_code}' and location name '{location_name}'",
                                status_code=status.HTTP_400_BAD_REQUEST
                            )
                    
                    if qty_used_value > current_total_used:
                        # FIFO Consumption - need more parts
                        qty_to_consume = qty_used_value - current_total_used
                        
                        # Use existing InventoryService FIFO allocation
                        allocation_result = InventoryService.allocate_inventory_fifo(
                            part_id=str(work_order_part.part.id),
                            qty_needed=qty_to_consume,
                            allocation_type='consume',
                            coded_location=location_value,  # Use original coded location
                            work_order_part=work_order_part,
                            performed_by=params.get('user'),
                            notes=f"Direct consumption for WOP {work_order_part.id}"
                        )
                        
                        # Create WOPR records for each batch consumed
                        wopr_records_created = []
                        for batch_detail in allocation_result['batch_details']:
                            batch = InventoryBatch.objects.get(id=batch_detail['batch_id'])
                            
                            # Ensure we have a valid unit cost
                            unit_cost = batch.last_unit_cost or 0
                            
                            wopr = WorkOrderPartRequest.objects.create(
                                work_order_part=work_order_part,
                                inventory_batch=batch,
                                qty_used=batch_detail['qty_allocated'],
                                unit_cost_snapshot=unit_cost,
                                total_parts_cost=batch_detail['qty_allocated'] * unit_cost,
                                # All workflow flags remain False (direct consumption)
                            )
                            wopr_records_created.append({
                                'id': str(wopr.id),
                                'qty_used': wopr.qty_used,
                                'batch_id': str(wopr.inventory_batch.id),
                                'unit_cost': float(wopr.unit_cost_snapshot),
                                'total_cost': float(wopr.total_parts_cost)
                            })
                        
                        response_data.update({
                            'operation_type': 'consumption_fifo',
                            'message': f'Consumed {qty_to_consume} parts using FIFO. Total qty_used now: {qty_used_value}',
                            'allocation_result': allocation_result,
                            'wopr_records_created': wopr_records_created,
                            'total_consumed': qty_to_consume
                        })
                        
                    elif qty_used_value < current_total_used:
                        # LIFO Return - returning parts
                        qty_to_return = current_total_used - qty_used_value
                        
                        # Use InventoryService for LIFO return (reverse recent consumption)
                        return_result = InventoryService.reverse_consumption_lifo(
                            work_order_part=work_order_part,
                            qty_to_return=qty_to_return,
                            performed_by=params.get('user'),
                            notes=f"Direct return for WOP {work_order_part.id}"
                        )
                        
                        response_data.update({
                            'operation_type': 'return_lifo',
                            'message': f'Returned {qty_to_return} parts using LIFO. Total qty_used now: {qty_used_value}',
                            'return_result': return_result,
                            'total_returned': qty_to_return
                        })
                    else:
                        # No change needed
                        response_data.update({
                            'operation_type': 'no_change',
                            'message': f'qty_used already equals {qty_used_value}. No inventory changes made.',
                        })
                
                # Refresh and return updated data
                work_order_part.refresh_from_db()
                response_data['work_order_part'] = self.serializer_class(work_order_part).data
                
                # Include updated part requests
                updated_requests = work_order_part.part_requests.all()
                if updated_requests.exists():
                    response_data['work_order_part_requests'] = WorkOrderPartRequestBaseSerializer(updated_requests, many=True).data
                
                return self.format_response(data=response_data, status_code=200)
        
        except Exception as e:
            return self.handle_exception(e)
    
    def _validate_quantity(self, value, field_name):
        """Validate quantity field"""
        try:
            qty = int(value)
            if qty < 0:
                raise LocalBaseException(
                    exception=f"{field_name} cannot be negative",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            return qty
        except (ValueError, TypeError):
            raise LocalBaseException(
                exception=f"{field_name} must be a valid integer",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    





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
            workflow_service.request_parts(
                wop_id=pk,
                qty_needed=serializer.validated_data['qty_needed'],
                performed_by=request.user,
                notes=serializer.validated_data.get('notes'),
                **metadata
            )
            
            return self.format_response(
                data=serializer.data,
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
            workflow_service.confirm_availability(
                wopr_id=pk,
                performed_by=request.user,
                notes=serializer.validated_data.get('notes'),
                **metadata
            )
            
            return self.format_response(
                data=serializer.data,
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
            workflow_service.mark_ordered(
                wopr_id=pk,
                performed_by=request.user,
                notes=serializer.validated_data.get('notes'),
                **metadata
            )
            
            return self.format_response(
                data=serializer.data,
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
            workflow_service.deliver_parts(
                wopr_id=pk,
                performed_by=request.user,
                notes=serializer.validated_data.get('notes'),
                **metadata
            )
            
            return self.format_response(
                data=serializer.data,
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
            workflow_service.pickup_parts(
                wopr_id=pk,
                qty_picked_up=serializer.validated_data['qty_picked_up'],
                performed_by=request.user,
                notes=serializer.validated_data.get('notes'),
                **metadata
            )
            
            return self.format_response(
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
            
        except Exception as e:
            return self.handle_exception(e)
    
    def cancel_availability(self, request, pk=None):
        """
        POST /work-order-part-requests/{id}/cancel-availability
        Cancel parts request or availability (auto-detects based on current state)
        
        Auto-detection logic:
        - If is_available=True: Cancels warehouse availability
        - If is_available=False and is_requested=True: Cancels mechanic request
        - If is_ordered=True or is_delivered=True: Returns validation error
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
            
            # Call service (cancel_type is auto-detected)
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
            
            # Base queryset for requests needing warehouse attention:
            # - is_requested=True: Normal pending requests
            # - is_available=True: Cancelled requests awaiting acknowledgment
            from django.db.models import Q
            queryset = WorkOrderPartRequest.objects.filter(
                Q(is_requested=True) | Q(is_available=True)
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
                    "position": wopr.position,
                    'requested_at': first_requested.isoformat() if first_requested else None,
                    'created_at': wopr.created_at.isoformat(),
                    'available_inventory': available_inventory,
                    'total_available_qty': sum(inv['available_qty'] for inv in available_inventory),
                    'can_fulfill': sum(inv['available_qty'] for inv in available_inventory) >= (wopr.qty_needed or 0)
                }
                serialized_data.append(item_data)
            
            return self.format_response(
                data=serialized_data,
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


