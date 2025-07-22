from pm_automation.platforms.base.views import *
from pm_automation.platforms.mobile.serializers import *


class PmsettingsMobileView(PmsettingsBaseView):
    serializer_class = PmsettingsMobileSerializer


class PmtriggerMobileView(PmtriggerBaseView):
    serializer_class = PmtriggerMobileSerializer


class PMSettingsChecklistMobileView(PMSettingsChecklistBaseView):
    serializer_class = PMSettingsChecklistMobileSerializer


