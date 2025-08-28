from parts.platforms.base.views import *
from parts.platforms.mobile.serializers import *


class PartMobileView(PartBaseView):
    serializer_class = PartMobileSerializer


class InventorybatchMobileView(InventoryBatchBaseView):
    serializer_class = InventorybatchMobileSerializer


class WorkorderpartMobileView(WorkOrderPartBaseView):
    serializer_class = WorkorderpartMobileSerializer


class WorkorderpartrequestMobileView(WorkOrderPartRequestBaseView):
    serializer_class = WorkorderpartrequestMobileSerializer


class PartmovementMobileView(PartMovementBaseView):
    serializer_class = PartmovementMobileSerializer


class WorkOrderPartRequestWorkflowMobileView(WorkOrderPartRequestWorkflowBaseView):
    """Mobile view for WOPR workflow operations"""
    pass


class WorkOrderPartRequestLogMobileView(WorkOrderPartRequestLogBaseView):
    """Mobile view for WorkOrderPartRequestLog read-only operations"""
    serializer_class = WorkOrderPartRequestLogMobileSerializer


