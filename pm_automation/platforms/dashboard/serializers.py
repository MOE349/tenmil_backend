from pm_automation.platforms.base.serializers import *


class PmsettingsDashboardSerializer(PmsettingsBaseSerializer):
    pass


class PmtriggerDashboardSerializer(PmtriggerBaseSerializer):
    pass


class PMSettingsChecklistDashboardSerializer(PMSettingsChecklistSerializer):
    class Meta(PMSettingsChecklistSerializer.Meta):
        fields = ['id', 'name', 'pm_settings']


