from parts.platforms.base.views import *
from parts.platforms.mobile.serializers import *


class PartMobileView(PartBaseView):
    serializer_class = PartMobileSerializer


class InventoryBatchMobileView(InventoryBatchBaseView):
    serializer_class = InventoryBatchMobileSerializer


class WorkOrderPartMobileView(WorkOrderPartBaseView):
    serializer_class = WorkOrderPartMobileSerializer


class PartMovementLogMobileView(PartMovementLogBaseView):
    serializer_class = PartMovementLogMobileSerializer


