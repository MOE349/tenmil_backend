from parts.platforms.base.serializers import *


class PartApiSerializer(PartBaseSerializer):
    """API serializer for Part model with API-specific customizations"""
    pass


class InventoryBatchApiSerializer(InventoryBatchBaseSerializer):
    """API serializer for InventoryBatch model with API-specific customizations"""
    pass


class WorkOrderPartApiSerializer(WorkOrderPartBaseSerializer):
    """API serializer for WorkOrderPart model with API-specific customizations"""
    pass


class WorkOrderPartRequestApiSerializer(WorkOrderPartRequestBaseSerializer):
    """API serializer for WorkOrderPartRequest model with API-specific customizations"""
    pass


class WorkOrderPartRequestLogApiSerializer(WorkOrderPartRequestLogBaseSerializer):
    """API serializer for WorkOrderPartRequestLog model with API-specific customizations"""
    
    class Meta:
        model = None  # Will be set by the base serializer
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


class PartMovementApiSerializer(PartMovementBaseSerializer):
    """API serializer for PartMovement model with API-specific customizations"""
    pass


class WorkOrderPartMovementApiSerializer(WorkOrderPartMovementSerializer):
    """API serializer for WorkOrderPart movement logs with API-specific customizations"""
    pass


# Expose action serializers at API level
class ReceivePartsApiSerializer(ReceivePartsSerializer):
    """API serializer for receiving parts"""
    pass


class IssuePartsApiSerializer(IssuePartsSerializer):
    """API serializer for issuing parts"""
    pass


class ReturnPartsApiSerializer(ReturnPartsSerializer):
    """API serializer for returning parts"""
    pass


class TransferPartsApiSerializer(TransferPartsSerializer):
    """API serializer for transferring parts"""
    pass


class PartVendorRelationApiSerializer(PartVendorRelationBaseSerializer):
    """API serializer for PartVendorRelation model with API-specific customizations"""
    pass


