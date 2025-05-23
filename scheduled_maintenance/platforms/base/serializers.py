from configurations.base_features.serializers.base_serializer import BaseSerializer
from scheduled_maintenance.models import *


class ScheduledMaintenanceBaseSerializer(BaseSerializer):
    class Meta:
        model = ScheduledMaintenance
        fields = '__all__'


