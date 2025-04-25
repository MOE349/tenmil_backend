from financial_reports.platforms.base.views import *
from financial_reports.platforms.dashboard.serializers import *


class CapitalCostDashboardView(CapitalCostBaseView):
    serializer_class = CapitalCostDashboardSerializer


