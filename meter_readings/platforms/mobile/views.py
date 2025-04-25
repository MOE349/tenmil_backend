from meter_readings.platforms.base.views import *
from meter_readings.platforms.mobile.serializers import *


class MeterreadingMobileView(MeterReadingBaseView):
    serializer_class = MeterreadingMobileSerializer


