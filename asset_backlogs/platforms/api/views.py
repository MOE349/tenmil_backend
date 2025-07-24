from asset_backlogs.platforms.base.views import *
from asset_backlogs.platforms.api.serializers import *


class AssetBacklogApiView(AssetBacklogBaseView):
    serializer_class = AssetBacklogApiSerializer


