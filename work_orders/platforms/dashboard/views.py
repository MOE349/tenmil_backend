from work_orders.platforms.base.views import *
from work_orders.platforms.dashboard.serializers import *


class WorkOrderDashboardView(WorkOrderBaseView):
    serializer_class = WorkOrderDashboardSerializer


class WorkOrderChecklistDashboardView(WorkOrderChecklistBaseView):
    serializer_class = WorkOrderChecklistDashboardSerializer


class WorkOrderLogDashboardView(WorkOrderLogBaseView):
    serializer_class = WorkOrderLogDashboardSerializer


class WorkOrderMiscCostDashboardView(WorkOrderMiscCostBaseView):
    serializer_class = WorkOrderMiscCostDashboardSerializer


class WorkOrderStatusNamesDashboardView(WorkOrderStatusNamesBaseView):
    serializer_class = WorkOrderStatusNamesDashboardSerializer


class WorkOrderStatusControlsDashboardView(WorkOrderStatusControlsBaseView):
    serializer_class = WorkOrderStatusControlsDashboardSerializer


class WorkOrderCompletionNoteDashboardView(WorkOrderCompletionNoteBaseView):
    serializer_class = WorkOrderCompletionNoteDashboardSerializer


class WorkOrderImportBacklogsDashboardView(WorkOrderImportBacklogsView):
    """Dashboard view for importing asset backlogs into work order checklists"""
    serializer_class = WorkOrderDashboardSerializer


class WorkOrderCompletionDashboardView(WorkOrderCompletionView):
    """Dashboard view for handling work order completion with backlog management"""
    serializer_class = WorkOrderDashboardSerializer


