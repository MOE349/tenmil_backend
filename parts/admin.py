from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Part, InventoryBatch, WorkOrderPart, WorkOrderPartRequest, PartMovement, WorkOrderPartRequestLog


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ['part_number', 'name', 'make', 'category', 'last_price', 'created_at']
    list_filter = ['category', 'make', 'created_at']
    search_fields = ['part_number', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(InventoryBatch)
class InventoryBatchAdmin(admin.ModelAdmin):
    list_display = ['part', 'location', 'qty_on_hand', 'qty_reserved', 'last_unit_cost', 'received_date']
    list_filter = ['location', 'received_date', 'created_at']
    search_fields = ['part__part_number', 'part__name']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['part', 'location']


@admin.register(WorkOrderPart)
class WorkOrderPartAdmin(admin.ModelAdmin):
    list_display = ['work_order', 'part', 'created_at']
    list_filter = ['created_at']
    search_fields = ['work_order__code', 'part__part_number', 'part__name']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['work_order', 'part']


@admin.register(WorkOrderPartRequest)
class WorkOrderPartRequestAdmin(admin.ModelAdmin):
    list_display = ['work_order_part', 'qty_needed', 'qty_used', 'qty_available', 'qty_delivered', 'position', 'workflow_status', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'is_requested', 'is_available', 'is_ordered', 'is_delivered', 'created_at']
    search_fields = ['work_order_part__work_order__code', 'work_order_part__part__part_number', 'work_order_part__part__name', 'position']
    readonly_fields = ['total_parts_cost', 'created_at', 'updated_at']
    list_select_related = ['work_order_part__work_order', 'work_order_part__part', 'inventory_batch']
    
    def workflow_status(self, obj):
        """Display current workflow status"""
        statuses = []
        if obj.is_requested:
            statuses.append("Requested")
        if obj.is_available:
            statuses.append("Available")
        if obj.is_ordered:
            statuses.append("Ordered")
        if obj.is_delivered:
            statuses.append("Delivered")
        return " | ".join(statuses) if statuses else "Draft"
    workflow_status.short_description = "Workflow Status"


@admin.register(WorkOrderPartRequestLog)
class WorkOrderPartRequestLogAdmin(admin.ModelAdmin):
    list_display = ['work_order_part_request', 'action_type', 'performed_by', 'qty_in_action', 'qty_total_after_action', 'created_at']
    list_filter = ['action_type', 'created_at', 'performed_by']
    search_fields = [
        'work_order_part_request__work_order_part__work_order__code', 
        'work_order_part_request__work_order_part__part__part_number',
        'performed_by__email'
    ]
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['work_order_part_request__work_order_part__work_order', 'work_order_part_request__work_order_part__part', 'performed_by']
    
    def has_change_permission(self, request, obj=None):
        # Audit logs should be immutable after creation
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Audit logs should be immutable after creation
        return False


@admin.register(PartMovement)
class PartMovementAdmin(admin.ModelAdmin):
    list_display = ['part', 'movement_type', 'qty_delta', 'from_location', 'to_location', 'work_order', 'created_at']
    list_filter = ['movement_type', 'created_at', 'from_location', 'to_location']
    search_fields = ['part__part_number', 'part__name', 'work_order__code']
    readonly_fields = ['created_at', 'updated_at']
    list_select_related = ['part', 'from_location', 'to_location', 'work_order', 'inventory_batch']
    
    def has_change_permission(self, request, obj=None):
        # Part movements should be immutable after creation
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Part movements should be immutable after creation
        return False
