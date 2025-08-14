from configurations.base_features.views.base_api_view import BaseAPIView
from parts.models import *
from parts.platforms.base.serializers import *


class PartBaseView(BaseAPIView):
    serializer_class = PartBaseSerializer
    model_class = Part


class InventoryBatchBaseView(BaseAPIView):
    serializer_class = InventoryBatchBaseSerializer
    model_class = InventoryBatch


class WorkOrderPartBaseView(BaseAPIView):
    serializer_class = WorkOrderPartBaseSerializer
    model_class = WorkOrderPart


class PartMovementLogBaseView(BaseAPIView):
    serializer_class = PartMovementLogBaseSerializer
    model_class = PartMovementLog


