from parts.platforms.base.views import (
    PartBaseView, InventoryBatchBaseView, WorkOrderPartBaseView, PartMovementBaseView
)
from parts.platforms.mobile.serializers import (
    PartMobileSerializer, InventoryBatchMobileSerializer, 
    WorkOrderPartMobileSerializer, PartMovementMobileSerializer
)


class PartMobileView(PartBaseView):
    serializer_class = PartMobileSerializer


class InventoryBatchMobileView(InventoryBatchBaseView):
    serializer_class = InventoryBatchMobileSerializer


class WorkOrderPartMobileView(WorkOrderPartBaseView):
    serializer_class = WorkOrderPartMobileSerializer


class PartMovementMobileView(PartMovementBaseView):
    serializer_class = PartMovementMobileSerializer


