"""
API Views for Parts & Inventory Module
Production-grade endpoints with proper error handling and validation.
"""
from .serializers import *
from parts.platforms.base.views import *


class PartApiView(PartBaseView):
    serializer_class = PartApiSerializer


class InventoryBatchApiView(InventoryBatchBaseView):
    serializer_class = InventoryBatchApiSerializer


class WorkOrderPartApiView(WorkOrderPartBaseView):
    serializer_class = WorkOrderPartApiSerializer


class PartMovementApiView(PartMovementBaseView):
    serializer_class = PartMovementApiSerializer