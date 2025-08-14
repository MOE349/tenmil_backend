from configurations.base_features.views.base_api_view import BaseAPIView
from parts.models import Part, InventoryBatch, WorkOrderPart, PartMovement
from parts.platforms.base.serializers import (
    PartBaseSerializer, InventoryBatchBaseSerializer, WorkOrderPartBaseSerializer, 
    PartMovementBaseSerializer
)


class PartBaseView(BaseAPIView):
    serializer_class = PartBaseSerializer
    model_class = Part


class InventoryBatchBaseView(BaseAPIView):
    serializer_class = InventoryBatchBaseSerializer
    model_class = InventoryBatch


class WorkOrderPartBaseView(BaseAPIView):
    serializer_class = WorkOrderPartBaseSerializer
    model_class = WorkOrderPart


class PartMovementBaseView(BaseAPIView):
    serializer_class = PartMovementBaseSerializer
    model_class = PartMovement


