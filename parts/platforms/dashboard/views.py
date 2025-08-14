from parts.platforms.base.views import (
    PartBaseView, InventoryBatchBaseView, WorkOrderPartBaseView, PartMovementBaseView
)
from parts.platforms.dashboard.serializers import (
    PartDashboardSerializer, InventoryBatchDashboardSerializer, 
    WorkOrderPartDashboardSerializer, PartMovementDashboardSerializer
)


class PartDashboardView(PartBaseView):
    serializer_class = PartDashboardSerializer


class InventoryBatchDashboardView(InventoryBatchBaseView):
    serializer_class = InventoryBatchDashboardSerializer


class WorkOrderPartDashboardView(WorkOrderPartBaseView):
    serializer_class = WorkOrderPartDashboardSerializer


class PartMovementDashboardView(PartMovementBaseView):
    serializer_class = PartMovementDashboardSerializer


