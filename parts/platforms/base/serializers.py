from configurations.base_features.serializers.base_serializer import BaseSerializer
from parts.models import Part, InventoryBatch, WorkOrderPart, PartMovement


class PartBaseSerializer(BaseSerializer):
    class Meta:
        model = Part
        fields = '__all__'


class InventoryBatchBaseSerializer(BaseSerializer):
    class Meta:
        model = InventoryBatch
        fields = '__all__'


class WorkOrderPartBaseSerializer(BaseSerializer):
    class Meta:
        model = WorkOrderPart
        fields = '__all__'


class PartMovementBaseSerializer(BaseSerializer):
    class Meta:
        model = PartMovement
        fields = '__all__'


