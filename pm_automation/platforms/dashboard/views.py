from pm_automation.platforms.base.views import *
from pm_automation.platforms.dashboard.serializers import *


class PMSettingsDashboardView(PMSettingsBaseView):
    serializer_class = PMSettingsDashboardSerializer


class PMTriggerDashboardView(PMTriggerBaseView):
    serializer_class = PMTriggerDashboardSerializer


class PMIterationDashboardView(PMIterationBaseView):
    serializer_class = PMIterationDashboardSerializer


class PMIterationChecklistDashboardView(PMIterationChecklistBaseView):
    serializer_class = PMIterationChecklistDashboardSerializer


