from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Part, InventoryBatch, WorkOrderPart, PartMovement


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
    list_display = ['work_order', 'part', 'qty_used', 'unit_cost_snapshot', 'total_parts_cost', 'created_at']
    list_filter = ['created_at']
    search_fields = ['work_order__code', 'part__part_number', 'part__name']
    readonly_fields = ['total_parts_cost', 'created_at', 'updated_at']
    list_select_related = ['work_order', 'part', 'inventory_batch']


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
