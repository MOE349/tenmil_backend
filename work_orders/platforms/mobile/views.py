from work_orders.platforms.base.views import *
from work_orders.platforms.mobile.serializers import *


class WorkOrderMobileView(WorkOrderBaseView):
    serializer_class = WorkOrderMobileSerializer


class WorkOrderChecklistMobileView(WorkOrderChecklistBaseView):
    serializer_class = WorkOrderChecklistMobileSerializer


class WorkOrderLogMobileView(WorkOrderLogBaseView):
    serializer_class = WorkOrderLogMobileSerializer


class WorkOrderMiscCostMobileView(WorkOrderMiscCostBaseView):
    serializer_class = WorkOrderMiscCostMobileSerializer


