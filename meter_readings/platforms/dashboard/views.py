from meter_readings.platforms.base.views import *
from meter_readings.platforms.dashboard.serializers import *


class MeterreadingDashboardView(MeterReadingBaseView):
    serializer_class = MeterreadingDashboardSerializer


