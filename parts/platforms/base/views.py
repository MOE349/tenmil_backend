from rest_framework import status
from configurations.base_features.views.base_api_view import BaseAPIView
from parts.models import Part, InventoryBatch, WorkOrderPart, PartMovement
from parts.platforms.base.serializers import (
    PartBaseSerializer, InventoryBatchBaseSerializer, WorkOrderPartBaseSerializer, 
    PartMovementBaseSerializer
)
from parts.inventory_operations_views import InventoryOperationsBaseView


class PartBaseView(BaseAPIView):
    """Base view for Part CRUD operations"""
    serializer_class = PartBaseSerializer
    model_class = Part


class InventoryBatchBaseView(BaseAPIView):
    """Base view for InventoryBatch CRUD operations"""
    serializer_class = InventoryBatchBaseSerializer
    model_class = InventoryBatch


class WorkOrderPartBaseView(BaseAPIView):
    """Base view for WorkOrderPart CRUD operations"""
    serializer_class = WorkOrderPartBaseSerializer
    model_class = WorkOrderPart


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


