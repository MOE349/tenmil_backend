from fault_codes.platforms.base.views import *
from fault_codes.platforms.mobile.serializers import *


class FaultCodeMobileView(FaultCodeBaseView):
    serializer_class = FaultCodeMobileSerializer


