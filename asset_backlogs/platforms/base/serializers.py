from configurations.base_features.serializers.base_serializer import BaseSerializer
from asset_backlogs.models import *


class AssetBacklogBaseSerializer(BaseSerializer):
    class Meta:
        model = AssetBacklog
        fields = '__all__'


