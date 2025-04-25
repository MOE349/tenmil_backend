from configurations.base_features.views.base_api_view import BaseAPIView
from company.models import *
from company.platforms.base.serializers import *


class SiteBaseView(BaseAPIView):
    serializer_class = SiteBaseSerializer
    model_class = Site


class LocationBaseView(BaseAPIView):
    serializer_class = LocationBaseSerializer
    model_class = Location


