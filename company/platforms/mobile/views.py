from company.platforms.base.views import *
from company.platforms.mobile.serializers import *


class SiteMobileView(SiteBaseView):
    serializer_class = SiteMobileSerializer


class LocationMobileView(LocationBaseView):
    serializer_class = LocationMobileSerializer


