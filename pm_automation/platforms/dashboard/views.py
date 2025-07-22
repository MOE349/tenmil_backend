from pm_automation.platforms.base.views import *
from pm_automation.platforms.dashboard.serializers import *


class PmsettingsDashboardView(PmsettingsBaseView):
    serializer_class = PmsettingsDashboardSerializer


class PmtriggerDashboardView(PmtriggerBaseView):
    serializer_class = PmtriggerDashboardSerializer


class PMSettingsChecklistDashboardView(PMSettingsChecklistBaseView):
    serializer_class = PMSettingsChecklistDashboardSerializer


