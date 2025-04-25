from configurations.base_features.serializers.base_serializer import BaseSerializer
from meter_readings.models import *
from users.platforms.base.serializers import UserBaseSerializer


class MeterReadingBaseSerializer(BaseSerializer):
    class Meta:
        model = MeterReading
        fields = '__all__'

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['created_by'] = UserBaseSerializer(instance.created_by).data
        return response
