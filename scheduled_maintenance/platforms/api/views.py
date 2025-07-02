from scheduled_maintenance.platforms.base.views import *
from scheduled_maintenance.platforms.api.serializers import *


class ScheduledMaintenanceApiView(ScheduledMaintenanceBaseView):
    serializer_class = ScheduledMaintenanceApiSerializer


class SmIttirationCycleApiView(SmIttirationCycleBaseView):
    serializer_class = SmIttirationCycleApiSerializer


class SmLogApiView(SmLogBaseView):
    serializer_class = SmLogApiSerializer


class SmIttirationCycleChecklistApiView(SmIttirationCycleChecklistBaseView):
    serializer_class = SmIttirationCycleChecklistApiSerializer


class SMInfoApiView(SMInfoBaseView):
    serializer_class = SMInfoApiSerializer
