from company.platforms.base.views import *
from company.platforms.dashboard.serializers import *


class SiteDashboardView(SiteBaseView):
    serializer_class = SiteDashboardSerializer


class LocationDashboardView(LocationBaseView):
    serializer_class = LocationDashboardSerializer


