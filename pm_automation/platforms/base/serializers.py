from configurations.base_features.serializers.base_serializer import BaseSerializer
from pm_automation.models import *
from rest_framework import serializers



class PMIterationChecklistSerializer(BaseSerializer):
    class Meta:
        model = PMIterationChecklist
        fields = '__all__'


class PMIterationPartsSerializer(BaseSerializer):
    class Meta:
        model = PMIterationParts
        fields = '__all__'
    
    def mod_to_representation(self, instance):
        response = super().mod_to_representation(instance)
        response['id'] = str(instance.id)
        
        # Add part details
        if instance.part:
            response['part'] = {
                "id": str(instance.part.id),
                "part_number": instance.part.part_number,
                "name": instance.part.name,
                "last_price": str(instance.part.last_price) if instance.part.last_price else None,
                "end_point": "/parts/part"
            }
            response['part_number'] = instance.part.part_number
        # Add computed fields
        if instance.part and instance.part.last_price:
            response['estimated_total_cost'] = str(instance.part.last_price * instance.qty_needed)
        
        return response


class PMIterationSerializer(BaseSerializer):
    checklist_items = PMIterationChecklistSerializer(many=True, read_only=True)
    parts = PMIterationPartsSerializer(many=True, read_only=True)
    
    class Meta:
        model = PMIteration
        fields = '__all__'


class PMSettingsBaseSerializer(BaseSerializer):
    iterations = PMIterationSerializer(many=True, read_only=True, source='iterations.all')
    
    class Meta:
        model = PMSettings
        fields = '__all__'

    def validate(self, data):
        content_type = data.get('content_type')
        object_id = data.get('object_id')
        trigger_type = data.get('trigger_type')
        
        # Check PM settings limit per trigger type
        qs = PMSettings.objects.filter(
            content_type=content_type, 
            object_id=object_id,
            trigger_type=trigger_type
        )
        # Exclude self in case of update
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.count() >= 3:  # Allow up to 3 PM settings per asset per trigger type
            trigger_type_display = dict(PMTriggerTypes.choices).get(trigger_type, trigger_type)
            raise serializers.ValidationError(f'Each asset can have at most 3 {trigger_type_display} PM automation configurations.')
        
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
        has_work_orders = PMTrigger.objects.filter(
            pm_settings=instance, 
            work_order__is_closed=False, 
            work_order__is_pm_generated=True,
            is_handled=False
        ).exists()
        
        if has_work_orders:
            # Different display logic for different PM types
            if instance.trigger_type == PMTriggerTypes.METER_READING:
                # For METER PMs: show next_trigger_value
                if instance.next_trigger_value is not None:
                    response['next_trigger_value'] = f"{int(instance.next_trigger_value)}?"
            elif instance.trigger_type == PMTriggerTypes.CALENDAR:
                # For CALENDAR PMs: show next_due_date
                if instance.next_due_date is not None:
                    response['next_due_date'] = f"{instance.next_due_date}?"
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


