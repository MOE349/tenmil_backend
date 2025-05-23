from configurations.base_features.views.base_api_view import BaseAPIView
from scheduled_maintenance.models import *
from scheduled_maintenance.platforms.base.serializers import *


class ScheduledMaintenanceBaseView(BaseAPIView):
    serializer_class = ScheduledMaintenanceBaseSerializer
    model_class = ScheduledMaintenance


