from work_orders.platforms.base.views import *
from work_orders.platforms.api.serializers import *
from rest_framework import status
from rest_framework.decorators import action
from work_orders.models import WorkOrder, WorkOrderChecklist
from work_orders.platforms.api.serializers import WorkOrderChecklistApiSerializer


class WorkOrderApiView(WorkOrderBaseView):
    serializer_class = WorkOrderApiSerializer


class WorkOrderChecklistApiView(WorkOrderChecklistBaseView):
    """API View for WorkOrderChecklist CRUD operations"""
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


