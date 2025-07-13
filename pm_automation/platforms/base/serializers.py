from configurations.base_features.serializers.base_serializer import BaseSerializer
from pm_automation.models import *
from rest_framework import serializers


class PMSettingsBaseSerializer(BaseSerializer):
    class Meta:
        model = PMSettings
        fields = '__all__'

    def validate(self, data):
        content_type = data.get('content_type')
        object_id = data.get('object_id')
        qs = PMSettings.objects.filter(content_type=content_type, object_id=object_id)
        # Exclude self in case of update
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.count() >= 3:
            raise serializers.ValidationError('Each asset can have at most 3 PM automations.')
        return data


class PMTriggerBaseSerializer(BaseSerializer):
    class Meta:
        model = PMTrigger
        fields = '__all__'


