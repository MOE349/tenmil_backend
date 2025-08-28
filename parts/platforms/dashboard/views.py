from parts.platforms.base.views import *
from parts.platforms.dashboard.serializers import *


class PartDashboardView(PartBaseView):
    serializer_class = PartDashboardSerializer


class InventorybatchDashboardView(InventoryBatchBaseView):
    serializer_class = InventorybatchDashboardSerializer


class WorkorderpartDashboardView(WorkOrderPartBaseView):
    serializer_class = WorkorderpartDashboardSerializer


class WorkorderpartrequestDashboardView(WorkOrderPartRequestBaseView):
    serializer_class = WorkorderpartrequestDashboardSerializer


class PartmovementDashboardView(PartMovementBaseView):
    serializer_class = PartmovementDashboardSerializer


class WorkOrderPartRequestWorkflowDashboardView(WorkOrderPartRequestWorkflowBaseView):
    """Dashboard view for WOPR workflow operations"""
    pass


class WorkOrderPartRequestLogDashboardView(WorkOrderPartRequestLogBaseView):
    """Dashboard view for WorkOrderPartRequestLog read-only operations"""
    serializer_class = WorkOrderPartRequestLogDashboardSerializer


