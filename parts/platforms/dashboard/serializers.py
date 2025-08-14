from parts.platforms.base.serializers import (
    PartBaseSerializer, InventoryBatchBaseSerializer, WorkOrderPartBaseSerializer, 
    PartMovementBaseSerializer
)


class PartDashboardSerializer(PartBaseSerializer):
    pass


class InventoryBatchDashboardSerializer(InventoryBatchBaseSerializer):
    pass


class WorkOrderPartDashboardSerializer(WorkOrderPartBaseSerializer):
    pass


class PartMovementDashboardSerializer(PartMovementBaseSerializer):
    pass


