from asset_backlogs.platforms.base.views import *
from asset_backlogs.platforms.mobile.serializers import *


class AssetBacklogMobileView(AssetBacklogBaseView):
    serializer_class = AssetBacklogMobileSerializer


