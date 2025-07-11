from fault_codes.platforms.base.views import *
from fault_codes.platforms.api.serializers import *


class FaultCodeApiView(FaultCodeBaseView):
    serializer_class = FaultCodeApiSerializer


