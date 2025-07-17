from assets.models import Equipment
from assets.platforms.base.serializers import AssetBaseSerializer
from assets.services import get_asset_serializer
from configurations.base_features.db.db_helpers import get_object_by_content_type_and_id
from configurations.base_features.serializers.base_serializer import BaseSerializer
from core.models import WorkOrderStatusControls
from tenant_users.platforms.base.serializers import TenantUserBaseSerializer
from work_orders.models import *
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from django.utils import timezone


class WorkOrderBaseSerializer(BaseSerializer):
    class Meta:
        model = WorkOrder
        fields = '__all__'
    
    def to_representation(self, instance):
        response = super().to_representation(instance)
        asset = get_object_by_content_type_and_id(instance.content_type.id, instance.object_id)
        response['asset'] = get_asset_serializer(asset).data
        response['status'] = WorkOrderStatusNamesBaseSerializer(instance.status).data
        response['completion_note'] = str(WorkOrderCompletionNote.objects.get_or_create(work_order=instance).id)
        return response


class WorkOrderChecklistBaseSerializer(BaseSerializer):
    class Meta:
        model = WorkOrderChecklist
        fields = '__all__'

    def validate_hrs_spent(self, value):
        """Validate that hrs_spent is numeric and positive"""
        if value is not None and (not isinstance(value, (int, float)) or value < 0):
            raise serializers.ValidationError("hrs_spent must be a positive number")
        return value
    
    def validate_completion_date(self, value):
        """Validate completion_date is not in the future"""
        if value and value > timezone.now():
            raise serializers.ValidationError("completion_date cannot be in the future")
        return value

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['work_order'] = WorkOrderBaseSerializer(instance.work_order).data
        if instance.completed_by:
            response['completed_by'] = TenantUserBaseSerializer(instance.completed_by).data
        else:
            response['completed_by'] = None
        return response

class WorkOrderLogBaseSerializer(BaseSerializer):
    class Meta:
        model = WorkOrderLog
        fields = '__all__'

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['work_order'] = WorkOrderBaseSerializer(instance.work_order).data
        response['user'] =  TenantUserBaseSerializer(instance.user).data
        return response


class WorkOrderMiscCostBaseSerializer(BaseSerializer):
    class Meta:
        model = WorkOrderMiscCost
        fields = '__all__'


class WorkOrderStatusNamesBaseSerializer(BaseSerializer):
    class Meta:
        model = WorkOrderStatusNames
        fields = '__all__'

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['control'] = {"name": instance.control.name, "id": instance.control.id}
        return response

class WorkOrderStatusControlsBaseSerializer(BaseSerializer):
    class Meta:
        model = WorkOrderStatusControls
        fields = '__all__'

class WorkOrderCompletionNoteBaseSerializer(BaseSerializer):
    class Meta:
        model = WorkOrderCompletionNote
        fields = '__all__'

    def to_representation(self, instance):
        response = super().to_representation(instance)
        checklists = WorkOrderChecklist.objects.filter(work_order=instance.work_order)
        hrs_spent = sum(checklist.hrs_spent for checklist in checklists)
        response['total_hrs_spent'] = hrs_spent
        completed_by = [checklist.completed_by for checklist in checklists]
        response['completed_by'] = TenantUserBaseSerializer(completed_by, many =True).data
        return response