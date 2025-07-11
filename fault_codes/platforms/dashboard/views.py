from fault_codes.platforms.base.views import *
from fault_codes.platforms.dashboard.serializers import *


class FaultCodeDashboardView(FaultCodeBaseView):
    serializer_class = FaultCodeDashboardSerializer


