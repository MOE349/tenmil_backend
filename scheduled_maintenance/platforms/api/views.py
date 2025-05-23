from scheduled_maintenance.platforms.base.views import *
from scheduled_maintenance.platforms.api.serializers import *


class ScheduledMaintenanceApiView(ScheduledMaintenanceBaseView):
    serializer_class = ScheduledMaintenanceApiSerializer


