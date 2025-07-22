from pm_automation.platforms.base.serializers import *


class PmsettingsMobileSerializer(PmsettingsBaseSerializer):
    pass


class PmtriggerMobileSerializer(PmtriggerBaseSerializer):
    pass


class PMSettingsChecklistMobileSerializer(PMSettingsChecklistSerializer):
    class Meta(PMSettingsChecklistSerializer.Meta):
        fields = ['id', 'name', 'pm_settings']


