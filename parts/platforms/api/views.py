from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework import viewsets

from parts.platforms.base.views import (
    PartBaseView, InventoryBatchBaseView, WorkOrderPartBaseView, 
    PartMovementBaseView, InventoryOperationsBaseView
)
from parts.platforms.api.serializers import (
    PartApiSerializer, InventoryBatchApiSerializer, WorkOrderPartApiSerializer,
    PartMovementApiSerializer
)


class PartApiView(PartBaseView):
    """API view for Part CRUD operations"""
    serializer_class = PartApiSerializer


class InventoryBatchApiView(InventoryBatchBaseView):
    """API view for InventoryBatch CRUD operations"""
    serializer_class = InventoryBatchApiSerializer


class WorkOrderPartApiView(WorkOrderPartBaseView):
    """API view for WorkOrderPart CRUD operations"""
    serializer_class = WorkOrderPartApiSerializer


class WorkOrderPartReturnApiView(WorkOrderPartBaseView):
    """API view for returning parts from work orders back to inventory"""
    
    def post(self, request, *args, **kwargs):
        """Return parts from work order to inventory"""
        return self.return_parts_to_inventory(request)


class PartMovementApiView(PartMovementBaseView):
    """API view for PartMovement read-only operations"""
    serializer_class = PartMovementApiSerializer


class InventoryOperationsApiView(InventoryOperationsBaseView, viewsets.ViewSet):
    """API view for inventory operations (receive, issue, return, transfer)"""
    
    @action(detail=False, methods=['post'], url_path='receive')
    def receive(self, request):
        """Receive parts into inventory"""
        return super().receive_parts(request)
    
    @action(detail=False, methods=['post'], url_path='issue')
    def issue(self, request):
        """Issue parts to work order"""
        return super().issue_parts(request)
    
    @action(detail=False, methods=['post'], url_path='return')
    def return_parts_action(self, request):
        """Return parts from work order"""
        return super().return_parts(request)
    
    @action(detail=False, methods=['post'], url_path='transfer')
    def transfer(self, request):
        """Transfer parts between locations"""
        return super().transfer_parts(request)
    
    @action(detail=False, methods=['get'], url_path='on-hand')
    def on_hand(self, request):
        """Get on-hand quantities"""
        return super().get_on_hand(request)
    
    @action(detail=False, methods=['get'], url_path='batches')
    def batches(self, request):
        """Get inventory batches"""
        return super().get_batches(request)
    
    @action(detail=False, methods=['get'], url_path='movements')
    def movements(self, request):
        """Get part movements"""
        return super().get_movements(request)
    
    @action(detail=False, methods=['get'], url_path='locations-on-hand')
    def locations_on_hand(self, request):
        """Get all locations with on-hand quantities for a specific part"""
        return super().get_locations_on_hand(request)
    
    @action(detail=False, methods=['get'], url_path='get-part-location')
    def get_part_locations(self, request):
        """Get part locations with simplified numbered response format"""
        return super().get_part_locations(request)


