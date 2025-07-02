from assets.models import Equipment
from assets.platforms.base.serializers import AssetBaseSerializer
from assets.services import get_asset_serializer
from configurations.base_features.db.db_helpers import get_object_by_content_type_and_id
from configurations.base_features.serializers.base_serializer import BaseSerializer
from core.models import WorkOrderStatusControls
from tenant_users.platforms.base.serializers import TenantUserBaseSerializer
from work_orders.models import *


class WorkOrderBaseSerializer(BaseSerializer):
    class Meta:
        model = WorkOrder
        fields = '__all__'
    
    def to_representation(self, instance):
        response = super().to_representation(instance)
        asset = get_object_by_content_type_and_id(instance.content_type.id, instance.object_id)
        response['asset'] = get_asset_serializer(asset).data
        response['status'] = WorkOrderStatusNamesBaseSerializer(instance.status).data
        return response


class WorkOrderChecklistBaseSerializer(BaseSerializer):
    class Meta:
        model = WorkOrderChecklist
        fields = '__all__'


    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['work_order'] = WorkOrderBaseSerializer(instance.work_order).data
        response['assigned_to'] =  TenantUserBaseSerializer(instance.assigned_to).data
        response['completed_by'] =  TenantUserBaseSerializer(instance.completed_by).data
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