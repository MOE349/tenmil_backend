from scheduled_maintenance.platforms.base.views import *
from scheduled_maintenance.platforms.mobile.serializers import *


class ScheduledMaintenanceMobileView(ScheduledMaintenanceBaseView):
    serializer_class = ScheduledMaintenanceMobileSerializer


