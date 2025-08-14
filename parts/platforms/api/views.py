from parts.platforms.base.views import *
from parts.platforms.api.serializers import *


class PartApiView(PartBaseView):
    serializer_class = PartApiSerializer


class InventoryBatchApiView(InventoryBatchBaseView):
    serializer_class = InventoryBatchApiSerializer


class WorkOrderPartApiView(WorkOrderPartBaseView):
    serializer_class = WorkOrderPartApiSerializer


class PartMovementLogApiView(PartMovementLogBaseView):
    serializer_class = PartMovementLogApiSerializer


