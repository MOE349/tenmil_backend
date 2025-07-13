from configurations.base_features.serializers.base_serializer import BaseSerializer
from pm_automation.models import *


class PMSettingsBaseSerializer(BaseSerializer):
    class Meta:
        model = PMSettings
        fields = '__all__'


class PMTriggerBaseSerializer(BaseSerializer):
    class Meta:
        model = PMTrigger
        fields = '__all__'


