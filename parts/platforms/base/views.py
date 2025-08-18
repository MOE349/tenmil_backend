from configurations.base_features.views.base_api_view import BaseAPIView
from parts.models import Part, InventoryBatch, WorkOrderPart, PartMovement
from parts.platforms.base.serializers import (
    PartBaseSerializer, InventoryBatchBaseSerializer, WorkOrderPartBaseSerializer, 
    PartMovementBaseSerializer
)


class PartBaseView(BaseAPIView):
    serializer_class = PartBaseSerializer
    model_class = Part

    """API view for Part management"""
    def get_queryset(self, params=None, ordering=None):
        """Get parts with optional filtering"""
        queryset = Part.objects.all()
        
        # Apply ordering if provided, otherwise use default
        if ordering:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('part_number')
        
        # Handle filtering params from query parameters or passed params
        query_params = params or getattr(self.request, 'query_params', {})
        
        # Filter by part number (partial match)
        part_number = query_params.get('part_number')
        if part_number:
            queryset = queryset.filter(part_number__icontains=part_number)
        
        # Filter by category
        category = query_params.get('category')
        if category:
            queryset = queryset.filter(category__icontains=category)
        
        # Filter by make
        make = query_params.get('make')
        if make:
            queryset = queryset.filter(make__icontains=make)
            
        return queryset

class InventoryBatchBaseView(BaseAPIView):
    """API view for InventoryBatch management"""
    serializer_class = InventoryBatchBaseSerializer
    model_class = InventoryBatch


    # def get_queryset(self, params=None, ordering=None):
    #     """Get batches with optional filtering"""
    #     queryset = InventoryBatch.objects.select_related('part', 'location')
        
    #     # Apply ordering if provided, otherwise use default
    #     if ordering:
    #         queryset = queryset.order_by(ordering)
    #     else:
    #         queryset = queryset.order_by('part__part_number', 'location__name', 'received_date')
        
    #     # Handle filtering params from query parameters or passed params
    #     query_params = params or getattr(self.request, 'query_params', {})
        
    #     # Filter by part
    #     part_id = query_params.get('part_id')
    #     if part_id:
    #         queryset = queryset.filter(part_id=part_id)
        
    #     # Filter by location
    #     location_id = query_params.get('location_id')
    #     if location_id:
    #         queryset = queryset.filter(location_id=location_id)
        
    #     # Show only batches with stock
    #     show_empty = query_params.get('show_empty', 'false').lower()
    #     if show_empty != 'true':
    #         queryset = queryset.filter(qty_on_hand__gt=0)
            
    #     return queryset


class WorkOrderPartBaseView(BaseAPIView):
    """API view for WorkOrderPart management"""
    serializer_class = WorkOrderPartBaseSerializer
    model_class = WorkOrderPart

    def get_queryset(self, params=None, ordering=None):
        """Get work order parts with optional filtering"""
        queryset = WorkOrderPart.objects.select_related(
            'work_order', 'part', 'inventory_batch'
        )
        
        # Apply ordering if provided, otherwise use default
        if ordering:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-created_at')
        
        # Handle filtering params from query parameters or passed params
        query_params = params or getattr(self.request, 'query_params', {})
        
        # Filter by work order
        work_order_id = query_params.get('work_order_id')
        if work_order_id:
            queryset = queryset.filter(work_order_id=work_order_id)
        
        # Filter by part
        part_id = query_params.get('part_id')
        if part_id:
            queryset = queryset.filter(part_id=part_id)
            
        return queryset

class PartMovementBaseView(BaseAPIView):
    """API view for PartMovement management"""
    serializer_class = PartMovementBaseSerializer
    model_class = PartMovement

    def get_queryset(self, params=None, ordering=None):
        """Get movements with optional filtering"""
        queryset = PartMovement.objects.select_related(
            'part', 'inventory_batch', 'from_location', 'to_location', 'work_order', 'created_by'
        )
        
        # Apply ordering if provided, otherwise use default
        if ordering:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-created_at')
        
        # Handle filtering params from query parameters or passed params
        query_params = params or getattr(self.request, 'query_params', {})
        
        # Filter by part
        part_id = query_params.get('part_id')
        if part_id:
            queryset = queryset.filter(part_id=part_id)
        
        # Filter by work order
        work_order_id = query_params.get('work_order_id')
        if work_order_id:
            queryset = queryset.filter(work_order_id=work_order_id)
        
        # Filter by movement type
        movement_type = query_params.get('movement_type')
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)
        
        # Date range filtering
        from_date = query_params.get('from_date')
        if from_date:
            queryset = queryset.filter(created_at__gte=from_date)
        
        to_date = query_params.get('to_date')
        if to_date:
            queryset = queryset.filter(created_at__lte=to_date)
        
        # Limit results for performance
        limit = min(int(query_params.get('limit', 100)), 1000)
        return queryset[:limit]