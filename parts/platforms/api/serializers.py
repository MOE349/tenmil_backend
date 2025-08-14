"""
API Serializers for Parts & Inventory Module
"""

from rest_framework import serializers
from decimal import Decimal

from configurations.base_features.serializers.base_serializer import BaseSerializer
from parts.models import Part, InventoryBatch, WorkOrderPart, PartMovement


class PartApiSerializer(BaseSerializer):
    """Serializer for Part model"""
    
    class Meta:
        model = Part
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_part_number(self, value):
        """Ensure part number is unique"""
        if not value or not value.strip():
            raise serializers.ValidationError("Part number cannot be empty")
        return value.strip().upper()

    def validate_last_price(self, value):
        """Validate last price is non-negative"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Last price cannot be negative")
        return value


class InventoryBatchApiSerializer(BaseSerializer):
    """Serializer for InventoryBatch model"""
    
    part_number = serializers.CharField(source='part.part_number', read_only=True)
    part_name = serializers.CharField(source='part.name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    qty_available = serializers.ReadOnlyField()
    total_value = serializers.ReadOnlyField()
    
    class Meta:
        model = InventoryBatch
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'qty_available', 'total_value')

    def validate(self, attrs):
        """Validate batch data"""
        qty_on_hand = attrs.get('qty_on_hand', 0)
        qty_reserved = attrs.get('qty_reserved', 0)
        
        if qty_reserved > qty_on_hand:
            raise serializers.ValidationError(
                "Reserved quantity cannot exceed quantity on hand"
            )
        
        return attrs


class WorkOrderPartApiSerializer(BaseSerializer):
    """Serializer for WorkOrderPart model"""
    
    part_number = serializers.CharField(source='part.part_number', read_only=True)
    part_name = serializers.CharField(source='part.name', read_only=True)
    work_order_code = serializers.CharField(source='work_order.code', read_only=True)
    
    class Meta:
        model = WorkOrderPart
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at', 'total_parts_cost')


class PartMovementApiSerializer(BaseSerializer):
    """Serializer for PartMovement model"""
    
    part_number = serializers.CharField(source='part.part_number', read_only=True)
    part_name = serializers.CharField(source='part.name', read_only=True)
    from_location_name = serializers.CharField(source='from_location.name', read_only=True)
    to_location_name = serializers.CharField(source='to_location.name', read_only=True)
    work_order_code = serializers.CharField(source='work_order.code', read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True)
    
    class Meta:
        model = PartMovement
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')


# Input/Output Serializers for Operations

class ReceivePartsInputSerializer(serializers.Serializer):
    """Input serializer for receiving parts"""
    part_id = serializers.UUIDField()
    location_id = serializers.UUIDField()
    qty = serializers.IntegerField(min_value=1)
    unit_cost = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.00'))
    received_date = serializers.DateField()
    receipt_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    idempotency_key = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_received_date(self, value):
        """Validate received date is not in the future"""
        from django.utils import timezone
        if value > timezone.now().date():
            raise serializers.ValidationError("Received date cannot be in the future")
        return value


class IssuePartsInputSerializer(serializers.Serializer):
    """Input serializer for issuing parts to work order"""
    work_order_id = serializers.UUIDField()
    part_id = serializers.UUIDField()
    location_id = serializers.UUIDField()
    qty = serializers.IntegerField(min_value=1)
    idempotency_key = serializers.CharField(max_length=255, required=False, allow_blank=True)


class ReturnPartsInputSerializer(serializers.Serializer):
    """Input serializer for returning parts from work order"""
    work_order_id = serializers.UUIDField()
    part_id = serializers.UUIDField()
    location_id = serializers.UUIDField()
    qty = serializers.IntegerField(min_value=1)
    idempotency_key = serializers.CharField(max_length=255, required=False, allow_blank=True)


class TransferPartsInputSerializer(serializers.Serializer):
    """Input serializer for transferring parts between locations"""
    part_id = serializers.UUIDField()
    from_location_id = serializers.UUIDField()
    to_location_id = serializers.UUIDField()
    qty = serializers.IntegerField(min_value=1)
    idempotency_key = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        """Validate that from and to locations are different"""
        if attrs['from_location_id'] == attrs['to_location_id']:
            raise serializers.ValidationError(
                "From and to locations must be different"
            )
        return attrs


class OnHandQuerySerializer(serializers.Serializer):
    """Query parameters for on-hand inventory"""
    part_id = serializers.UUIDField(required=False)
    location_id = serializers.UUIDField(required=False)


class BatchQuerySerializer(serializers.Serializer):
    """Query parameters for batch listing"""
    part_id = serializers.UUIDField(required=False)
    location_id = serializers.UUIDField(required=False)


class MovementQuerySerializer(serializers.Serializer):
    """Query parameters for movement history"""
    part_id = serializers.UUIDField(required=False)
    location_id = serializers.UUIDField(required=False)
    work_order_id = serializers.UUIDField(required=False)
    from_date = serializers.DateTimeField(required=False)
    to_date = serializers.DateTimeField(required=False)
    limit = serializers.IntegerField(min_value=1, max_value=1000, default=100)