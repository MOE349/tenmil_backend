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


class WorkOrderStatusNamesMobileView(WorkOrderStatusNamesBaseView):
    serializer_class = WorkOrderStatusNamesMobileSerializer


class WorkOrderStatusControlsMobileView(WorkOrderStatusControlsBaseView):
    serializer_class = WorkOrderStatusControlsMobileSerializer


class WorkOrderCompletionNoteMobileView(WorkOrderCompletionNoteBaseView):
    serializer_class = WorkOrderCompletionNoteMobileSerializer


class WorkOrderImportBacklogsMobileView(WorkOrderImportBacklogsView):
    """Mobile view for importing asset backlogs into work order checklists"""
    pass


class WorkOrderCompletionMobileView(WorkOrderCompletionView):
    """Mobile view for handling work order completion with backlog management"""
    pass


