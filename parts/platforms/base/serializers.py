from rest_framework import serializers
from decimal import Decimal
from typing import Dict, Any
from datetime import datetime, date
from django.utils import timezone

from configurations.base_features.serializers.base_serializer import BaseSerializer
from parts.models import Part, InventoryBatch, WorkOrderPart, PartMovement
from company.platforms.base.serializers import LocationBaseSerializer
from tenant_users.platforms.base.serializers import TenantUserBaseSerializer


class FlexibleDateTimeField(serializers.DateTimeField):
    """Custom DateTimeField that can handle both date and datetime objects"""
    
    def to_representation(self, value):
        if value is None:
            return None
            
        # Convert date to datetime if needed
        if isinstance(value, date) and not isinstance(value, datetime):
            value = timezone.make_aware(
                datetime.combine(value, datetime.min.time())
            )
        
        return super().to_representation(value)


class PartBaseSerializer(BaseSerializer):
    """Base serializer for Part model"""
    
    class Meta:
        model = Part
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")
    
    def mod_to_representation(self, instance):
        response = super().mod_to_representation(instance)
        response['id'] = str(instance.id)
        
        # Add computed fields
        response['total_on_hand'] = self._get_total_on_hand(instance)
        response['total_reserved'] = self._get_total_reserved(instance)
        
        return response
    
    def _get_total_on_hand(self, instance):
        """Get total quantity on hand across all locations"""
        from django.db.models import Sum
        return instance.inventory_batches.aggregate(
            total=Sum('qty_on_hand')
        )['total'] or Decimal('0')
    
    def _get_total_reserved(self, instance):
        """Get total quantity reserved across all locations"""
        from django.db.models import Sum
        return instance.inventory_batches.aggregate(
            total=Sum('qty_reserved')
        )['total'] or Decimal('0')


class InventoryBatchBaseSerializer(BaseSerializer):
    """Base serializer for InventoryBatch model"""
    
    # Use custom field to handle potential date/datetime issues
    received_date = FlexibleDateTimeField(required=False)
    
    class Meta:
        model = InventoryBatch
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")
    
    def mod_to_representation(self, instance):
        response = super().mod_to_representation(instance)
        response['id'] = str(instance.id)
        
        # Add related object details
        response['part'] = {
            "id": str(instance.part.id),
            "part_number": instance.part.part_number,
            "name": instance.part.name,
            "end_point": "/parts/part"
        }
        
        response['location'] = {
            "id": str(instance.location.id),
            "name": f"{instance.location.name} - {instance.location.site.name}",
            "end_point": "/company/location"
        }
        
        # Add computed fields
        response['available_qty'] = instance.qty_on_hand - instance.qty_reserved
        response['total_value'] = instance.qty_on_hand * instance.last_unit_cost
        
        return response


class WorkOrderPartBaseSerializer(BaseSerializer):
    """Base serializer for WorkOrderPart model"""
    
    class Meta:
        model = WorkOrderPart
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "total_parts_cost")
    
    def mod_to_representation(self, instance):
        response = super().mod_to_representation(instance)
        response['id'] = str(instance.id)
        
        # Add related object details
        response['work_order'] = {
            "id": str(instance.work_order.id),
            "code": instance.work_order.code,
            "end_point": "/work_orders/work_order"
        }
        
        response['part'] = {
            "id": str(instance.part.id),
            "part_number": instance.part.part_number,
            "name": instance.part.name,
            "end_point": "/parts/part"
        }
        
        response['inventory_batch'] = {
            "id": str(instance.inventory_batch.id),
            "received_date": instance.inventory_batch.received_date,
            "location": instance.inventory_batch.location.name,
            "end_point": "/parts/inventory_batch"
        }
        
        return response


class PartMovementBaseSerializer(BaseSerializer):
    """Base serializer for PartMovement model - read-only audit trail"""
    
    class Meta:
        model = PartMovement
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")  # All fields are read-only
    
    def mod_to_representation(self, instance):
        response = super().mod_to_representation(instance)
        response['id'] = str(instance.id)
        
        # Add related object details
        response['part'] = {
            "id": str(instance.part.id),
            "part_number": instance.part.part_number,
            "name": instance.part.name,
            "end_point": "/parts/part"
        }
        
        if instance.inventory_batch:
            response['inventory_batch'] = {
                "id": str(instance.inventory_batch.id),
                "received_date": instance.inventory_batch.received_date,
                "end_point": "/parts/inventory_batch"
            }
        
        if instance.from_location:
            response['from_location'] = {
                "id": str(instance.from_location.id),
                "name": instance.from_location.name,
                "end_point": "/company/location"
            }
        
        if instance.to_location:
            response['to_location'] = {
                "id": str(instance.to_location.id),
                "name": instance.to_location.name,
                "end_point": "/company/location"
            }
        
        if instance.work_order:
            response['work_order'] = {
                "id": str(instance.work_order.id),
                "code": instance.work_order.code,
                "end_point": "/work_orders/work_order"
            }
        
        if instance.created_by:
            response['created_by'] = {
                "id": str(instance.created_by.id),
                "username": instance.created_by.username,
                "end_point": "/tenant_users/tenant_user"
            }
        
        return response


# Action serializers for service operations

class ReceivePartsSerializer(serializers.Serializer):
    """Serializer for receiving parts into inventory"""
    part_id = serializers.UUIDField(required=True)
    location_id = serializers.UUIDField(required=True)
    qty = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal('0.001'))
    unit_cost = serializers.DecimalField(max_digits=10, decimal_places=4, min_value=Decimal('0'))
    received_date = serializers.DateTimeField(required=False)
    receipt_id = serializers.CharField(max_length=100, required=False)
    idempotency_key = serializers.CharField(max_length=100, required=False)


class IssuePartsSerializer(serializers.Serializer):
    """Serializer for issuing parts to work order"""
    work_order_id = serializers.UUIDField(required=True)
    part_id = serializers.UUIDField(required=True)
    location_id = serializers.UUIDField(required=True)
    qty = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal('0.001'))
    idempotency_key = serializers.CharField(max_length=100, required=False)


class ReturnPartsSerializer(serializers.Serializer):
    """Serializer for returning parts from work order"""
    work_order_id = serializers.UUIDField(required=True)
    part_id = serializers.UUIDField(required=True)
    location_id = serializers.UUIDField(required=True)
    qty = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal('0.001'))
    idempotency_key = serializers.CharField(max_length=100, required=False)


class TransferPartsSerializer(serializers.Serializer):
    """Serializer for transferring parts between locations"""
    part_id = serializers.UUIDField(required=True)
    from_location_id = serializers.UUIDField(required=True)
    to_location_id = serializers.UUIDField(required=True)
    qty = serializers.DecimalField(max_digits=10, decimal_places=3, min_value=Decimal('0.001'))
    idempotency_key = serializers.CharField(max_length=100, required=False)
    
    def validate(self, data):
        if data['from_location_id'] == data['to_location_id']:
            raise serializers.ValidationError("Source and destination locations must be different")
        return data


class OnHandQuerySerializer(serializers.Serializer):
    """Serializer for on-hand quantity queries"""
    part_id = serializers.UUIDField(required=False)
    location_id = serializers.UUIDField(required=False)


class MovementQuerySerializer(serializers.Serializer):
    """Serializer for movement history queries"""
    part_id = serializers.UUIDField(required=False)
    location_id = serializers.UUIDField(required=False)
    work_order_id = serializers.UUIDField(required=False)
    from_date = serializers.DateTimeField(required=False)
    to_date = serializers.DateTimeField(required=False)
    limit = serializers.IntegerField(min_value=1, max_value=1000, default=100)


class LocationOnHandQuerySerializer(serializers.Serializer):
    """Serializer for location on-hand quantity queries"""
    part_id = serializers.UUIDField(required=True, help_text="Part ID to get location quantities for")
    location_id = serializers.UUIDField(required=True, help_text="Location ID to get location quantities for")


