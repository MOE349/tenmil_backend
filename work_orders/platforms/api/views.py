from work_orders.platforms.base.views import *
from work_orders.platforms.api.serializers import *
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


class WorkOrderStatusControlsApiView(WorkOrderStatusControlsBaseView):
    serializer_class = WorkOrderStatusControlsApiSerializer


class WorkOrderCompletionNoteApiView(WorkOrderCompletionNoteBaseView):
    serializer_class = WorkOrderCompletionNoteApiSerializer


class WorkOrderImportBacklogsApiView(WorkOrderImportBacklogsView):
    """API view for importing asset backlogs into work order checklists"""
    pass


class WorkOrderCompletionApiView(WorkOrderCompletionView):
    """API view for handling work order completion with backlog management"""
    pass


class MaintenanceTypeApiView(MaintenanceTypeBaseView):
    serializer_class = MaintenanceTypeApiSerializer

class HighLevelMaintenanceTypeApiView(HighLevelMaintenanceTypeBaseView):
    serializer_class = HighLevelMaintenanceTypeApiSerializer
