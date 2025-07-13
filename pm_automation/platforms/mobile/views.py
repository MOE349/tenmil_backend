from pm_automation.platforms.base.views import *
from pm_automation.platforms.mobile.serializers import *


class PMSettingsMobileView(PMSettingsBaseView):
    serializer_class = PMSettingsMobileSerializer


class PMTriggerMobileView(PMTriggerBaseView):
    serializer_class = PMTriggerMobileSerializer


