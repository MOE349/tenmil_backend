from pm_automation.platforms.base.views import *
from pm_automation.platforms.api.serializers import *
from configurations.base_features.exceptions.base_exceptions import LocalBaseException


class PMSettingsApiView(PMSettingsBaseView):
    serializer_class = PMSettingsApiSerializer


class PMTriggerApiView(PMTriggerBaseView):
    serializer_class = PMTriggerApiSerializer


class PMIterationApiView(PMIterationBaseView):
    serializer_class = PMIterationApiSerializer
    

class PMIterationChecklistApiView(PMIterationChecklistBaseView):
    serializer_class = PMIterationChecklistApiSerializer


class ManualPMGenerationApiView(ManualPMGenerationBaseView):
    """API view for manual PM work order generation"""
    pass

