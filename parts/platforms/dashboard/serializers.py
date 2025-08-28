from parts.platforms.base.serializers import *


class PartDashboardSerializer(PartBaseSerializer):
    pass


class InventorybatchDashboardSerializer(InventoryBatchBaseSerializer):
    pass


class WorkorderpartDashboardSerializer(WorkOrderPartBaseSerializer):
    pass


class WorkorderpartrequestDashboardSerializer(WorkOrderPartRequestBaseSerializer):
    pass


class PartmovementDashboardSerializer(PartMovementBaseSerializer):
    pass


class WorkOrderPartRequestLogDashboardSerializer(WorkOrderPartRequestLogBaseSerializer):
    """Dashboard serializer for WorkOrderPartRequestLog model"""
    
    class Meta:
        model = None  # Will be set by the base serializer
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


