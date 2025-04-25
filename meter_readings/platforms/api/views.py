from meter_readings.platforms.base.views import *
from meter_readings.platforms.api.serializers import *


class MeterreadingApiView(MeterReadingBaseView):
    serializer_class = MeterreadingApiSerializer


