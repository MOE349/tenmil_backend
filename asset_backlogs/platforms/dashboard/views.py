from asset_backlogs.platforms.base.views import *
from asset_backlogs.platforms.dashboard.serializers import *


class AssetBacklogDashboardView(AssetBacklogBaseView):
    serializer_class = AssetBacklogDashboardSerializer


