from parts.platforms.base.views import *
from parts.platforms.dashboard.serializers import *


class PartDashboardView(PartBaseView):
    serializer_class = PartDashboardSerializer


class InventorybatchDashboardView(InventorybatchBaseView):
    serializer_class = InventorybatchDashboardSerializer


class WorkorderpartDashboardView(WorkorderpartBaseView):
    serializer_class = WorkorderpartDashboardSerializer


class PartmovementDashboardView(PartmovementBaseView):
    serializer_class = PartmovementDashboardSerializer


