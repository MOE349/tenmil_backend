from parts.platforms.base.views import *
from parts.platforms.dashboard.serializers import *


class PartDashboardView(PartBaseView):
    serializer_class = PartDashboardSerializer


class InventoryBatchDashboardView(InventoryBatchBaseView):
    serializer_class = InventoryBatchDashboardSerializer


class WorkOrderPartDashboardView(WorkOrderPartBaseView):
    serializer_class = WorkOrderPartDashboardSerializer


class PartMovementLogDashboardView(PartMovementLogBaseView):
    serializer_class = PartMovementLogDashboardSerializer


