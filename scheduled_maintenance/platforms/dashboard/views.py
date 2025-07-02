from scheduled_maintenance.platforms.base.views import *
from scheduled_maintenance.platforms.dashboard.serializers import *


class ScheduledMaintenanceDashboardView(ScheduledMaintenanceBaseView):
    serializer_class = ScheduledMaintenanceDashboardSerializer


class SmIttirationCycleDashboardView(SmIttirationCycleBaseView):
    serializer_class = SmIttirationCycleDashboardSerializer


class SmLogDashboardView(SmLogBaseView):
    serializer_class = SmLogDashboardSerializer


