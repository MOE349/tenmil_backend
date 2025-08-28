from parts.platforms.base.serializers import *


class PartMobileSerializer(PartBaseSerializer):
    pass


class InventorybatchMobileSerializer(InventoryBatchBaseSerializer):
    pass


class WorkorderpartMobileSerializer(WorkOrderPartBaseSerializer):
    pass


class WorkorderpartrequestMobileSerializer(WorkOrderPartRequestBaseSerializer):
    pass


class PartmovementMobileSerializer(PartMovementBaseSerializer):
    pass


class WorkOrderPartRequestLogMobileSerializer(WorkOrderPartRequestLogBaseSerializer):
    """Mobile serializer for WorkOrderPartRequestLog model"""
    
    class Meta:
        model = None  # Will be set by the base serializer
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


