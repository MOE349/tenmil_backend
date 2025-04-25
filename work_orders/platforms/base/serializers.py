from assets.models import Equipment
from assets.platforms.base.serializers import EquipmentBaseSerializer
from configurations.base_features.serializers.base_serializer import BaseSerializer
from users.platforms.base.serializers import UserBaseSerializer
from work_orders.models import *


class WorkOrderBaseSerializer(BaseSerializer):
    class Meta:
        model = WorkOrder
        fields = '__all__'
    
    def to_representation(self, instance):
        response = super().to_representation(instance)
        asset = Equipment.objects.get(asset_ptr=instance.asset)
        response['asset'] = EquipmentBaseSerializer(asset).data
        response['status'] = WorkOrderStatusNamesBaseSerializer(instance.status).data
        return response


class WorkOrderChecklistBaseSerializer(BaseSerializer):
    class Meta:
        model = WorkOrderChecklist
        fields = '__all__'


    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['work_order'] = WorkOrderBaseSerializer(instance.work_order).data
        response['assigned_to'] =  UserBaseSerializer(instance.assigned_to).data
        response['completed_by'] =  UserBaseSerializer(instance.completed_by).data
        return response

class WorkOrderLogBaseSerializer(BaseSerializer):
    class Meta:
        model = WorkOrderLog
        fields = '__all__'

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['work_order'] = WorkOrderBaseSerializer(instance.work_order).data
        response['user'] =  UserBaseSerializer(instance.user).data
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