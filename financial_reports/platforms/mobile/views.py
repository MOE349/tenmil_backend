from financial_reports.platforms.base.views import *
from financial_reports.platforms.mobile.serializers import *


class CapitalCostMobileView(CapitalCostBaseView):
    serializer_class = CapitalCostMobileSerializer


