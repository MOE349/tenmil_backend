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
        if qs.count() >= 3:  # Allow up to 3 PM settings per asset
            raise serializers.ValidationError('Each asset can have at most 3 PM automation configurations.')
        return data

    def to_representation(self, instance):
        response = super().to_representation(instance)
        # Add asset information
        try:
            if hasattr(instance, 'asset') and instance.asset:
                response['asset_info'] = {
                    'id': str(instance.asset.id),
                    'code': instance.asset.code,
                    'name': instance.asset.name,
                    'type': f"{instance.content_type.app_label}.{instance.content_type.model}"
                }
        except Exception:
            # If asset access fails, provide basic info
            response['asset_info'] = {
                'type': f"{instance.content_type.app_label}.{instance.content_type.model}",
                'object_id': str(instance.object_id)
            }
        return response


class PMTriggerBaseSerializer(BaseSerializer):
    class Meta:
        model = PMTrigger
        fields = '__all__'

    def to_representation(self, instance):
        response = super().to_representation(instance)
        # Add PM settings information
        if instance.pm_settings:
            response['pm_settings_info'] = {
                'id': str(instance.pm_settings.id),
                'interval': f"{instance.pm_settings.interval_value} {instance.pm_settings.interval_unit}"
            }
        # Add work order information
        if instance.work_order:
            response['work_order_info'] = {
                'id': str(instance.work_order.id),
                'code': instance.work_order.code,
                'description': instance.work_order.description
            }
        return response


