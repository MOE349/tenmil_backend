from rest_framework import serializers
from decimal import Decimal
from typing import Dict, Any
from datetime import datetime, date
from django.utils import timezone

from configurations.base_features.serializers.base_serializer import BaseSerializer
from parts.models import Part, InventoryBatch, WorkOrderPart, WorkOrderPartRequest, PartMovement
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
        response ['code'] = f"{instance.part_number} - {instance.name}"
        return response
    
    def _get_total_on_hand(self, instance):
        """Get total quantity on hand across all locations"""
        from django.db.models import Sum
        return instance.inventory_batches.aggregate(
            total=Sum('qty_on_hand')
        )['total'] or 0
    
    def _get_total_reserved(self, instance):
        """Get total quantity reserved across all locations"""
        from django.db.models import Sum
        return instance.inventory_batches.aggregate(
            total=Sum('qty_reserved')
        )['total'] or 0


class InventoryBatchBaseSerializer(BaseSerializer):
    """Base serializer for InventoryBatch model"""
    
    # Use custom field to handle potential date/datetime issues
    received_date = FlexibleDateTimeField(required=False)
    
    class Meta:
        model = InventoryBatch
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")
    
    # NOTE: create() method removed - all creation logic moved to service layer
    # InventoryBatch creation should go through inventory_service.receive_parts_from_data()
    # to ensure movement logs and business logic are properly handled
    
    def update(self, instance, validated_data):
        """
        Update InventoryBatch - do NOT auto-set qty_on_hand for updates
        Only new records get the auto-setting behavior
        """
        return super().update(instance, validated_data)
    
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
        read_only_fields = ("id", "created_at", "updated_at")
    
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
            "part_name": instance.part.name,
            "end_point": "/parts/part"
        }
        response["part_name"] = instance.part.name
        
        # Include total qty_used and qty_needed from all related part requests
        from django.db.models import Sum, Max, Q
        aggregates = instance.part_requests.aggregate(
            total_qty_used=Sum('qty_used'),
            # qty_needed should only include records that are not approved and not delivered
            total_qty_needed=Sum('qty_needed'),
            total_qty_available=Sum('qty_available'),
            total_qty_delivered=Sum('qty_delivered')
        )
        response['qty_used'] = aggregates['total_qty_used'] or 0
        response['qty_needed'] = aggregates['total_qty_needed'] or 0
        response['qty_available'] = aggregates['total_qty_available'] or 0
        response['qty_delivered'] = aggregates['total_qty_delivered'] or 0
        
        # Business Logic for WOP Status (based on workflow diagram)
        # Treat all WOPRs under a WOP as a cohesive unit
        total_needed = response['qty_needed']
        total_available = response['qty_available']
        total_delivered = response['qty_delivered']
        
        # Get counts for additional logic
        from django.db.models import Count
        wopr_counts = instance.part_requests.aggregate(
            total_wopr_count=Count('id'),
            requested_count=Count('id', filter=Q(is_requested=True)),
            available_count=Count('id', filter=Q(is_available=True)),
            ordered_count=Count('id', filter=Q(is_ordered=True)),
            delivered_count=Count('id', filter=Q(is_delivered=True))
        )
        
        # WOP Status Logic based on workflow requirements:
        
        # 1. IS_REQUESTED: Only when mechanic has actually submitted a request
        response['is_requested'] = (wopr_counts['requested_count'] or 0) > 0
        
        # 2. IS_AVAILABLE: We have some availability AND it's been marked available
        response['is_available'] = (
            total_available > 0 and 
            (wopr_counts['available_count'] or 0) > 0
        )
        
        # 3. IS_ORDERED: Any WOPR is ordered (for parts not available)
        response['is_ordered'] = (wopr_counts['ordered_count'] or 0) > 0
        
        # 4. IS_DELIVERED: Only when ALL WOPRs are delivered
        response['is_delivered'] = (
            wopr_counts['total_wopr_count'] > 0 and 
            wopr_counts['delivered_count'] == wopr_counts['total_wopr_count']
        )
        
        # Enhanced workflow status with granular states matching the diagram
        workflow_statuses = []
        
        if not response['is_requested']:
            workflow_statuses.append('Draft')
        else:
            if response['is_delivered']:
                if total_delivered >= total_needed:
                    workflow_statuses.append('Fully Delivered')
                else:
                    workflow_statuses.append('Partially Delivered')
            elif response['is_ordered']:
                workflow_statuses.append('Ordered')
            elif response['is_available']:
                if total_available >= total_needed:
                    workflow_statuses.append('Fully Available')
                else:
                    workflow_statuses.append('Partially Available')
            else:
                workflow_statuses.append('Requested')
        
        response['workflow_status'] = ' | '.join(workflow_statuses) if workflow_statuses else 'Draft'
        
        # Enhanced fulfillment indicators based on workflow diagram
        response['can_fulfill'] = total_available >= total_needed if total_needed > 0 else True
        response['is_fully_delivered'] = total_delivered >= total_needed if total_needed > 0 else False
        response['is_partially_delivered'] = 0 < total_delivered < total_needed if total_needed > 0 else False
        response['fulfillment_percentage'] = (total_delivered / total_needed * 100) if total_needed > 0 else 0
        
        # Additional status indicators based on workflow
        response['needs_ordering'] = (
            response['is_requested'] and 
            not response['is_available'] and 
            not response['is_ordered'] and
            total_available < total_needed
        )
        
        response['ready_for_pickup'] = (
            response['is_available'] and 
            total_available >= total_needed and
            not response['is_delivered']
        )
        
        response['awaiting_delivery'] = (
            response['is_ordered'] and 
            not response['is_delivered']
        )
        
        return response


class WorkOrderPartRequestBaseSerializer(BaseSerializer):
    """Base serializer for WorkOrderPartRequest model"""
    
    class Meta:
        model = WorkOrderPartRequest
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at", "total_parts_cost")
    
    def mod_to_representation(self, instance):
        response = super().mod_to_representation(instance)
        response['id'] = str(instance.id)
        
        # Add related object details
        response['work_order_part'] = {
            "id": str(instance.work_order_part.id),
            "work_order_code": instance.work_order_part.work_order.code,
            "part_number": instance.work_order_part.part.part_number,
            "end_point": "/parts/work_order_part"
        }
        if instance.inventory_batch:
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
                "email": instance.created_by.email,
                "name": instance.created_by.name,
                "end_point": "/tenant_users/tenant_user"
            }
        
        return response


# Action serializers for service operations

class ReceivePartsSerializer(serializers.Serializer):
    """Serializer for receiving parts into inventory"""
    part_id = serializers.UUIDField(required=True)
    location_id = serializers.UUIDField(required=True)
    qty = serializers.IntegerField(min_value=1)
    unit_cost = serializers.DecimalField(max_digits=10, decimal_places=4, min_value=Decimal('0'))
    received_date = serializers.DateTimeField(required=False)
    receipt_id = serializers.CharField(max_length=100, required=False)
    idempotency_key = serializers.CharField(max_length=100, required=False)


class IssuePartsSerializer(serializers.Serializer):
    """Serializer for issuing parts to work order"""
    work_order_id = serializers.UUIDField(required=True)
    part_id = serializers.UUIDField(required=True)
    location_id = serializers.UUIDField(required=True)
    qty = serializers.IntegerField(min_value=1)
    idempotency_key = serializers.CharField(max_length=100, required=False)


class ReturnPartsSerializer(serializers.Serializer):
    """Serializer for returning parts from work order"""
    work_order_id = serializers.UUIDField(required=True)
    part_id = serializers.UUIDField(required=True)
    location_id = serializers.UUIDField(required=True)
    qty = serializers.IntegerField(min_value=1)
    idempotency_key = serializers.CharField(max_length=100, required=False)


class TransferPartsSerializer(serializers.Serializer):
    """
    Serializer for transferring parts between locations
    
    Supports flexible location input formats:
    - UUID: Standard location UUID
    - Location String: 'SITE_CODE - LOCATION_NAME - AA1/RR2/BB3 - qty: 75.5'
    
    Auto-detects format and converts location strings to UUIDs internally.
    
    Position Handling:
    - When using location strings, destination position is extracted and used for the transfer
    - Parts are moved to the exact aisle/row/bin specified in the destination location string
    
    Validation Rules:
    - Transfers within the same location are allowed if positions (aisle/row/bin) are different
    - Only identical location AND position combinations are rejected
    """
    part_id = serializers.UUIDField(required=True)
    from_location_id = serializers.CharField(required=False, 
                                           help_text="UUID or location string format: 'SITE_CODE - LOCATION_NAME - AA1/RR2/BB3 - qty: 75.5'")
    to_location_id = serializers.CharField(required=False,
                                         help_text="UUID or location string format: 'SITE_CODE - LOCATION_NAME - AA1/RR2/BB3 - qty: 75.5'")
    from_location_string = serializers.CharField(max_length=500, required=False, 
                                                help_text="Format: 'SITE_CODE - LOCATION_NAME - AA1/RR2/BB3 - qty: 75.5'")
    to_location_string = serializers.CharField(max_length=500, required=False,
                                              help_text="Format: 'SITE_CODE - LOCATION_NAME - AA1/RR2/BB3 - qty: 75.5'")
    qty = serializers.IntegerField(min_value=1)
    aisle = serializers.CharField(max_length=50, required=False, allow_blank=True)
    row = serializers.CharField(max_length=50, required=False, allow_blank=True)
    bin = serializers.CharField(max_length=50, required=False, allow_blank=True)
    idempotency_key = serializers.CharField(max_length=100, required=False)
    
    def _is_uuid(self, value: str) -> bool:
        """Check if a string is a valid UUID format"""
        import uuid
        try:
            uuid.UUID(value)
            return True
        except (ValueError, AttributeError):
            return False
    
    def _process_location_field(self, data: dict, id_field: str, string_field: str, field_name: str):
        """Process location ID or string field and convert to UUID"""
        from parts.services import location_decoder
        
        has_id = id_field in data and data[id_field]
        has_string = string_field in data and data[string_field]
        
        if not (has_id or has_string):
            raise serializers.ValidationError(f"Either {id_field} or {string_field} is required")
        
        if has_id and has_string:
            raise serializers.ValidationError(f"Provide either {id_field} or {string_field}, not both")
        
        # Create key to store position info for this location
        position_key = f"_{field_name.lower()}_position"
        
        # If we have an ID field, check if it's a UUID or location string
        if has_id:
            if self._is_uuid(data[id_field]):
                # It's a UUID, validate it exists
                import uuid
                try:
                    uuid_val = uuid.UUID(data[id_field])
                    # Convert back to string for consistency
                    data[id_field] = str(uuid_val)
                    # No position info available from UUID
                    data[position_key] = None
                    return
                except ValueError:
                    raise serializers.ValidationError(f"Invalid UUID format for {id_field}")
            else:
                # It's a location string, treat it like from_location_string/to_location_string
                location_string = data[id_field]
                try:
                    decoded = location_decoder.decode_location_string(location_string)
                    location = location_decoder.get_location_by_site_and_name(
                        decoded['site_code'], decoded['location_name']
                    )
                    if not location:
                        raise serializers.ValidationError(
                            f"{field_name} location not found: {decoded['site_code']} - {decoded['location_name']}"
                        )
                    data[id_field] = str(location.id)
                    
                    # Store position info for later comparison
                    data[position_key] = {
                        'aisle': decoded['aisle'],
                        'row': decoded['row'],
                        'bin': decoded['bin']
                    }
                    
                    # Store position separately for each location type
                    if field_name.lower() == 'to':
                        data['dest_aisle'] = decoded['aisle']
                        data['dest_row'] = decoded['row'] 
                        data['dest_bin'] = decoded['bin']
                    elif field_name.lower() == 'from':
                        data['source_aisle'] = decoded['aisle']
                        data['source_row'] = decoded['row']
                        data['source_bin'] = decoded['bin']
                        
                    # Use decoded aisle/row/bin if not explicitly provided (for compatibility)
                    if not data.get('aisle') and decoded['aisle']:
                        data['aisle'] = decoded['aisle']
                    if not data.get('row') and decoded['row']:
                        data['row'] = decoded['row']
                    if not data.get('bin') and decoded['bin']:
                        data['bin'] = decoded['bin']
                        
                except ValueError as e:
                    raise serializers.ValidationError(f"Invalid {field_name} location format: {str(e)}")
        
        # If we have a string field, decode it
        elif has_string:
            try:
                decoded = location_decoder.decode_location_string(data[string_field])
                location = location_decoder.get_location_by_site_and_name(
                    decoded['site_code'], decoded['location_name']
                )
                if not location:
                    raise serializers.ValidationError(
                        f"{field_name} location not found: {decoded['site_code']} - {decoded['location_name']}"
                    )
                data[id_field] = str(location.id)
                
                # Store position info for later comparison
                data[position_key] = {
                    'aisle': decoded['aisle'],
                    'row': decoded['row'],
                    'bin': decoded['bin']
                }
                
                # Store position separately for each location type
                if field_name.lower() == 'to':
                    data['dest_aisle'] = decoded['aisle']
                    data['dest_row'] = decoded['row'] 
                    data['dest_bin'] = decoded['bin']
                elif field_name.lower() == 'from':
                    data['source_aisle'] = decoded['aisle']
                    data['source_row'] = decoded['row']
                    data['source_bin'] = decoded['bin']
                    
                # Use decoded aisle/row/bin if not explicitly provided (for compatibility)
                if not data.get('aisle') and decoded['aisle']:
                    data['aisle'] = decoded['aisle']
                if not data.get('row') and decoded['row']:
                    data['row'] = decoded['row']
                if not data.get('bin') and decoded['bin']:
                    data['bin'] = decoded['bin']
                    
            except ValueError as e:
                raise serializers.ValidationError(f"Invalid {string_field}: {str(e)}")

    def validate(self, data):
        # Process from location
        self._process_location_field(data, 'from_location_id', 'from_location_string', 'From')
        
        # Process to location  
        self._process_location_field(data, 'to_location_id', 'to_location_string', 'To')
        
        # Check if source and destination are exactly the same (location + position)
        if data['from_location_id'] == data['to_location_id']:
            # Same location - check if position is also the same
            from_position = data.get('_from_position')
            to_position = data.get('_to_position')
            
            # If we have position info from location strings, compare them
            if from_position and to_position:
                same_position = (
                    from_position['aisle'] == to_position['aisle'] and
                    from_position['row'] == to_position['row'] and  
                    from_position['bin'] == to_position['bin']
                )
                
                if same_position:
                    raise serializers.ValidationError(
                        "Source and destination must be different. Same location and position are not allowed."
                    )
            else:
                # Fallback: compare explicit aisle/row/bin fields or reject same location
                explicit_aisle = data.get('aisle', '') or ''
                explicit_row = data.get('row', '') or ''
                explicit_bin = data.get('bin', '') or ''
                
                # If no explicit position provided and same location, reject
                if not any([explicit_aisle, explicit_row, explicit_bin]):
                    raise serializers.ValidationError(
                        "Source and destination locations are the same. Please specify different aisle/row/bin or use different locations."
                    )
        
        # Use destination position if available, otherwise fall back to generic position
        if 'dest_aisle' in data or 'dest_row' in data or 'dest_bin' in data:
            # Prefer destination-specific position for the transfer
            # Use None instead of empty string for null positions
            data['aisle'] = data.get('dest_aisle') or data.get('aisle') or None
            data['row'] = data.get('dest_row') or data.get('row') or None
            data['bin'] = data.get('dest_bin') or data.get('bin') or None
        
        # Set source position data for position-based FIFO
        if 'source_aisle' in data or 'source_row' in data or 'source_bin' in data:
            data['from_aisle'] = data.get('source_aisle')
            data['from_row'] = data.get('source_row')
            data['from_bin'] = data.get('source_bin')
        
        # Clean up temporary position data
        data.pop('_from_position', None)
        data.pop('_to_position', None)
        data.pop('dest_aisle', None)
        data.pop('dest_row', None)
        data.pop('dest_bin', None)
        data.pop('source_aisle', None)
        data.pop('source_row', None)
        data.pop('source_bin', None)
        
        return data


class CreateWorkOrderPartRequestSerializer(serializers.Serializer):
    """Serializer for creating work order part requests"""
    work_order_part_id = serializers.UUIDField(required=True)
    inventory_batch_id = serializers.UUIDField(required=True)
    qty_needed = serializers.IntegerField(min_value=1, required=False)
    qty_used = serializers.IntegerField(required=True)
    unit_cost_snapshot = serializers.DecimalField(max_digits=10, decimal_places=4, min_value=Decimal('0'))
    is_approved = serializers.BooleanField(default=False)


class ApproveWorkOrderPartRequestSerializer(serializers.Serializer):
    """Serializer for approving work order part requests"""
    request_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="List of WorkOrderPartRequest IDs to approve"
    )


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


class WorkOrderPartMovementSerializer(PartMovementBaseSerializer):
    """Serializer for WorkOrderPart movement logs with custom calculations"""
    
    class Meta:
        model = PartMovement
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")  # All fields are read-only
    
    def mod_to_representation(self, instance):
        response = super().mod_to_representation(instance)
        
        # Modify qty_delta by multiplying by -1
        response['qty_delta'] = instance.qty_delta * -1
        
        # Add part_price from inventory_batch.last_unit_cost
        part_price = None
        if instance.inventory_batch:
            part_price = instance.inventory_batch.last_unit_cost
        response['part_price'] = str(part_price) if part_price is not None else None
        
        # Add total_price calculation: inventory_batch.last_unit_cost * qty_delta * -1
        total_price = None
        if instance.inventory_batch and instance.inventory_batch.last_unit_cost is not None:
            total_price = instance.inventory_batch.last_unit_cost * instance.qty_delta * -1
        response['total_price'] = str(total_price) if total_price is not None else None
        
        return response


# Workflow Serializers for WorkOrderPartRequest Actions

class RequestPartsSerializer(serializers.Serializer):
    """Serializer for mechanic requesting parts"""
    qty_needed = serializers.IntegerField(
        min_value=1,
        help_text="Quantity of parts needed"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Optional notes about the request"
    )


class ConfirmAvailabilitySerializer(serializers.Serializer):
    """Serializer for warehouse keeper confirming parts availability using position field"""
    qty_available = serializers.IntegerField(
        min_value=1,
        help_text="Quantity available for reservation"
    )
    position = serializers.CharField(
        max_length=200,
        help_text="Position in format 'SITE_CODE - LOCATION_NAME - A#/R#/B# - qty: #.#' (e.g., 'RC - MOUNTAIN - A1/R2/B3 - qty: 15.0')"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Optional notes about availability"
    )
    
    def validate_position(self, value):
        """Validate position format and extract location information"""
        try:
            # Position format: "SITE_CODE - LOCATION_NAME - A#/R#/B# - qty: #.#"
            parts = value.split(' - ')
            if len(parts) < 3:
                raise ValueError("Invalid position format")
            
            site_code = parts[0].strip()
            location_name = parts[1].strip()
            aisle_row_bin = parts[2].strip()
            
            # Validate aisle/row/bin format (A#/R#/B#)
            if not aisle_row_bin or '/' not in aisle_row_bin:
                raise ValueError("Invalid aisle/row/bin format")
                
        except Exception as e:
            raise serializers.ValidationError(
                f"Invalid position format: {str(e)}. Expected: 'SITE_CODE - LOCATION_NAME - A#/R#/B# - qty: #.#' (e.g., 'RC - MOUNTAIN - A1/R2/B3 - qty: 15.0')"
            )
        
        # Validate location exists
        try:
            from company.models import Location
            Location.objects.select_related('site').get(
                site__code=site_code,
                name=location_name
            )
        except Location.DoesNotExist:
            raise serializers.ValidationError(f"Location not found for site code '{site_code}' and location name '{location_name}'")
        
        return value


class MarkOrderedSerializer(serializers.Serializer):
    """Serializer for marking parts as ordered externally"""
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Optional notes about the order"
    )


class DeliverPartsSerializer(serializers.Serializer):
    """Serializer for warehouse keeper marking parts as delivered"""
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Optional notes about delivery"
    )


class PickupPartsSerializer(serializers.Serializer):
    """Serializer for mechanic picking up parts"""
    qty_picked_up = serializers.IntegerField(
        min_value=1,
        help_text="Quantity being picked up"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Optional notes about pickup"
    )


class CancelAvailabilitySerializer(serializers.Serializer):
    """Serializer for cancelling parts availability (auto-detects cancel type)"""
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Optional notes about cancellation"
    )


class WorkOrderPartRequestLogBaseSerializer(BaseSerializer):
    """Base serializer for WorkOrderPartRequestLog"""
    
    class Meta:
        model = None  # Will be set by platform-specific serializers
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def mod_to_representation(self, instance):
        response = super().mod_to_representation(instance)
        
        # Add computed fields
        if instance.performed_by:
            response['performed_by_email'] = instance.performed_by.email
            response['performed_by_name'] = f"{instance.performed_by.first_name} {instance.performed_by.last_name}".strip()
        
        if instance.work_order_part_request:
            response['work_order_code'] = instance.work_order_part_request.work_order_part.work_order.code
            response['part_number'] = instance.work_order_part_request.work_order_part.part.part_number
            response['part_name'] = instance.work_order_part_request.work_order_part.part.name
        
        # Format action type for display
        response['action_type_display'] = instance.get_action_type_display()
        
        return response

