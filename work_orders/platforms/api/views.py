from work_orders.platforms.base.views import *
from work_orders.platforms.api.serializers import *


class WorkOrderApiView(WorkOrderBaseView):
    serializer_class = WorkOrderApiSerializer


class WorkOrderChecklistApiView(WorkOrderChecklistBaseView):
    serializer_class = WorkOrderChecklistApiSerializer


class WorkOrderLogApiView(WorkOrderLogBaseView):
    serializer_class = WorkOrderLogApiSerializer


class WorkOrderMiscCostApiView(WorkOrderMiscCostBaseView):
    serializer_class = WorkOrderMiscCostApiSerializer


class WorkOrderStatusNamesApiView(WorkOrderStatusNamesBaseView):
    serializer_class = WorkOrderStatusNamesApiSerializer


class WorkOrderControlsApiView(WorkOrderStatusControlsBaseView):
    serializer_class = WorkOrderStatusControlsApiSerializer


class WWorkOrderCompletionNoteApiView(WorkOrderCompletionNoteBaseView):
    serializer_class = WorkOrderCompletionNoteApiSerializer


