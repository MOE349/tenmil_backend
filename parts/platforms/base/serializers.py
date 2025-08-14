from configurations.base_features.serializers.base_serializer import BaseSerializer
from parts.models import *


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


class PartMovementLogBaseSerializer(BaseSerializer):
    class Meta:
        model = PartMovementLog
        fields = '__all__'


