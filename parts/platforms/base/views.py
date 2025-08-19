from rest_framework import status
from decimal import Decimal
from datetime import datetime
from django.core.exceptions import ValidationError
from configurations.base_features.views.base_api_view import BaseAPIView
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
        from decimal import Decimal
        from django.db import transaction
        from work_orders.models import WorkOrder
        
        try:
            with transaction.atomic():
                # Get work order and determine location
                work_order_id = data.get('work_order')
                if not work_order_id:
                    return self.format_response(
                        None, 
                        ["work_order field is required"], 
                        status.HTTP_400_BAD_REQUEST
                    )
                
                try:
                    work_order = WorkOrder.objects.get(id=work_order_id)
                except WorkOrder.DoesNotExist:
                    return self.format_response(
                        None, 
                        ["Work order not found"], 
                        status.HTTP_404_NOT_FOUND
                    )
                
                # Get location from work order's asset using GenericForeignKey resolution
                from configurations.base_features.db.db_helpers import get_object_by_content_type_and_id
                
                try:
                    asset = get_object_by_content_type_and_id(
                        work_order.content_type.id, 
                        str(work_order.object_id)
                    )
                except Exception as e:
                    return self.format_response(
                        None, 
                        ["Work order asset not found"], 
                        status.HTTP_404_NOT_FOUND
                    )
                
                if not hasattr(asset, 'location') or not asset.location:
                    return self.format_response(
                        None, 
                        ["Work order asset does not have a valid location"], 
                        status.HTTP_400_BAD_REQUEST
                    )
                
                location = asset.location
                
                # Get part and validate
                part_id = data.get('part')
                if not part_id:
                    return self.format_response(
                        None, 
                        ["part field is required"], 
                        status.HTTP_400_BAD_REQUEST
                    )
                
                try:
                    part = Part.objects.get(id=part_id)
                except Part.DoesNotExist:
                    return self.format_response(
                        None, 
                        ["Part not found"], 
                        status.HTTP_404_NOT_FOUND
                    )
                
                # Get qty_used from data
                qty_used = data.get('qty_used')
                if not qty_used or Decimal(str(qty_used)) <= 0:
                    return self.format_response(
                        None, 
                        ["qty_used must be a positive value"], 
                        status.HTTP_400_BAD_REQUEST
                    )
                
                qty_used = Decimal(str(qty_used))
                
                # Get inventory batches for this part and location, ordered by received_date (FIFO)
                available_batches = InventoryBatch.objects.filter(
                    part=part,
                    location=location,
                    qty_on_hand__gt=0
                ).order_by('received_date')
                
                if not available_batches.exists():
                    return self.format_response(
                        None, 
                        [f"No inventory available for part {part.part_number} at location {location.name}"], 
                        status.HTTP_400_BAD_REQUEST
                    )
                
                # Check if we have enough total inventory
                total_available = sum(batch.qty_on_hand for batch in available_batches)
                if total_available < qty_used:
                    return self.format_response(
                        None, 
                        [f"Insufficient inventory. Requested: {qty_used}, Available: {total_available}"], 
                        status.HTTP_400_BAD_REQUEST
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


class PartMovementBaseView(BaseAPIView):
    """Base view for PartMovement read-only operations"""
    serializer_class = PartMovementBaseSerializer
    model_class = PartMovement
    
    # Part movements are immutable - disable write operations
    def create(self, request, *args, **kwargs):
        return self.format_response(
            None, 
            ["Part movements are immutable and created automatically"], 
            status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def update(self, request, pk=None, *args, **kwargs):
        return self.format_response(
            None, 
            ["Part movements are immutable"], 
            status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def destroy(self, request, pk=None, *args, **kwargs):
        return self.format_response(
            None, 
            ["Part movements are immutable"], 
            status.HTTP_405_METHOD_NOT_ALLOWED
        )


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
                return self.format_response(None, ["part_id or part parameter is required"], status.HTTP_400_BAD_REQUEST)
            if not location_id:
                return self.format_response(None, ["location_id or location parameter is required"], status.HTTP_400_BAD_REQUEST)
            
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
                        return self.format_response(None, [f"Part '{part_id}' not found by ID or part number"], status.HTTP_404_NOT_FOUND)
                else:
                    return self.format_response(None, [f"Part with ID {part_id} does not exist"], status.HTTP_404_NOT_FOUND)
            
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
                        return self.format_response(None, [f"Location '{location_id}' not found by ID or name"], status.HTTP_404_NOT_FOUND)
                else:
                    return self.format_response(None, [f"Location with ID {location_id} does not exist"], status.HTTP_404_NOT_FOUND)
            
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
                return self.format_response(None, ["No inventory batches found matching the criteria"], status.HTTP_404_NOT_FOUND)
            
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
        """Get part movements with optional filtering"""
        try:
            # Parse query parameters - support both formats
            part_id = request.query_params.get('part_id') or request.query_params.get('part')
            location_id = request.query_params.get('location_id') or request.query_params.get('location')
            work_order_id = request.query_params.get('work_order_id') or request.query_params.get('work_order')
            from_date = request.query_params.get('from_date')
            to_date = request.query_params.get('to_date')
            limit = int(request.query_params.get('limit', 100))
            
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
                limit=limit
            )
            
            # Serialize the movements
            serializer = PartMovementBaseSerializer(movements, many=True, context={'request': request})
            
            return self.format_response(serializer.data, None, status.HTTP_200_OK)
            
        except Exception as e:
            return self.handle_exception(e)
    
    def get_locations_on_hand(self, request):
        """Get all locations with aggregated inventory batch records for a specific part"""
        try:
            # Validate query parameters - support both formats
            part_id = request.query_params.get('part_id') or request.query_params.get('part')
            if not part_id:
                return self.format_response(None, ["part_id or part parameter is required"], status.HTTP_400_BAD_REQUEST)
            
            serializer = LocationOnHandQuerySerializer(data={'part_id': part_id})
            if not serializer.is_valid():
                return self.format_response(None, serializer.errors, status.HTTP_400_BAD_REQUEST)
            
            validated_part_id = serializer.validated_data['part_id']
            
            # Verify part exists
            try:
                part = Part.objects.get(id=validated_part_id)
            except Part.DoesNotExist:
                return self.format_response(None, [f"Part with ID {validated_part_id} does not exist"], status.HTTP_404_NOT_FOUND)
            
            # Get all inventory batches for this part with location details
            from django.db.models import Sum
            from company.models import Location
            
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
            
            # Format the response data
            response_data = []
            
            for item in inventory_data:
                # Only include items with positive quantities
                if item['total_qty_on_hand'] > 0:
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
                        'aisle': item['aisle'] or '',
                        'row': item['row'] or '',
                        'bin': item['bin'] or '',
                        'qty_on_hand': str(item['total_qty_on_hand'])
                    })
            
            return self.format_response(response_data, None, status.HTTP_200_OK)
            
        except Exception as e:
            return self.handle_exception(e)


