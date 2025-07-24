from configurations.base_features.views.base_api_view import BaseAPIView
from asset_backlogs.models import *
from asset_backlogs.platforms.base.serializers import *


class AssetBacklogBaseView(BaseAPIView):
    serializer_class = AssetBacklogBaseSerializer
    model_class = AssetBacklog


