from company.platforms.base.views import *
from company.platforms.api.serializers import *


class SiteApiView(SiteBaseView):
    serializer_class = SiteApiSerializer


class LocationApiView(LocationBaseView):
    serializer_class = LocationApiSerializer


