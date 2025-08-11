from work_orders.platforms.base.serializers import *


class WorkOrderApiSerializer(WorkOrderBaseSerializer):
    pass


class WorkOrderChecklistApiSerializer(WorkOrderChecklistBaseSerializer):
    """API Serializer for WorkOrderChecklist with validation"""
    pass
    
    
class WorkOrderLogApiSerializer(WorkOrderLogBaseSerializer):
    pass


class WorkOrderMiscCostApiSerializer(WorkOrderMiscCostBaseSerializer):
    pass


class WorkOrderStatusNamesApiSerializer(WorkOrderStatusNamesBaseSerializer):
    pass


class WorkOrderStatusControlsApiSerializer(WorkOrderStatusControlsBaseSerializer):
    pass


class WorkOrderCompletionNoteApiSerializer(WorkOrderCompletionNoteBaseSerializer):
    pass


class MaintenanceTypeApiSerializer(MaintenanceTypeBaseSerializer):
    pass


class HighLevelMaintenanceTypeApiSerializer(HighLevelMaintenanceTypeBaseSerializer):
    pass

