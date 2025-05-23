from scheduled_maintenance.platforms.base.views import *
from scheduled_maintenance.platforms.dashboard.serializers import *


class ScheduledMaintenanceDashboardView(ScheduledMaintenanceBaseView):
    serializer_class = ScheduledMaintenanceDashboardSerializer


