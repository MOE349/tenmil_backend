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


