from pm_automation.platforms.base.views import *
from pm_automation.platforms.api.serializers import *


class PMSettingsApiView(PMSettingsBaseView):
    serializer_class = PMSettingsApiSerializer


class PMTriggerApiView(PMTriggerBaseView):
    serializer_class = PMTriggerApiSerializer


class PMSettingsChecklistApiView(PMSettingsChecklistBaseView):
    serializer_class = PMSettingsChecklistApiSerializer


