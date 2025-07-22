from pm_automation.platforms.base.serializers import *


class PMSettingsApiSerializer(PMSettingsBaseSerializer):
    pass


class PMTriggerApiSerializer(PMTriggerBaseSerializer):
    pass


class PMSettingsChecklistApiSerializer(PMSettingsChecklistSerializer):
    class Meta(PMSettingsChecklistSerializer.Meta):
        fields = ['id', 'name', 'pm_settings']


