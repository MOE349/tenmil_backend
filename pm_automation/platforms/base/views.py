from configurations.base_features.views.base_api_view import BaseAPIView
from pm_automation.models import *
from pm_automation.platforms.base.serializers import *


class PMSettingsBaseView(BaseAPIView):
    serializer_class = PMSettingsBaseSerializer
    model_class = PMSettings


class PMTriggerBaseView(BaseAPIView):
    serializer_class = PMTriggerBaseSerializer
    model_class = PMTrigger


class PMIterationBaseView(BaseAPIView):
    serializer_class = PMIterationSerializer
    model_class = PMIteration


class PMIterationChecklistBaseView(BaseAPIView):
    serializer_class = PMIterationChecklistSerializer
    model_class = PMIterationChecklist


