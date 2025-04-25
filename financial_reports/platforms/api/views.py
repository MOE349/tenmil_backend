from financial_reports.platforms.base.views import *
from financial_reports.platforms.api.serializers import *


class CapitalCostApiView(CapitalCostBaseView):
    serializer_class = CapitalCostApiSerializer


