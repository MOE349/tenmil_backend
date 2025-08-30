from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import Part, InventoryBatch, WorkOrderPart, WorkOrderPartRequest, PartMovement, WorkOrderPartRequestLog, PartVendorRelation


class PartVendorRelationInline(admin.TabularInline):
    """Inline admin for PartVendorRelation within Part admin"""
    model = PartVendorRelation
    extra = 1
    fields = ('vendor', 'is_primary')
    readonly_fields = ()


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ['part_number', 'name', 'make', 'category', 'last_price', 'get_vendor_count', 'created_at']
    list_filter = ['category', 'make', 'created_at']
    search_fields = ['part_number', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PartVendorRelationInline]
    
    def get_vendor_count(self, obj):
        """Display number of vendors for this part"""
        count = obj.vendor_relations.count()
        primary_count = obj.vendor_relations.filter(is_primary=True).count()
        return format_html(
            '<span style="color: {};">{} ({} primary)</span>',
            'green' if primary_count > 0 else 'orange',
            count,
            primary_count
        )
    get_vendor_count.short_description = 'Vendors'


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


@admin.register(PartVendorRelation)
class PartVendorRelationAdmin(admin.ModelAdmin):
    list_display = (
        'part', 
        'vendor', 
        'is_primary_display',
        'created_at'
    )
    list_filter = ('is_primary', 'created_at')
    search_fields = ('part__part_number', 'part__name', 'vendor__name', 'vendor__code')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Relation Information', {
            'fields': ('part', 'vendor', 'is_primary')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def is_primary_display(self, obj):
        """Display primary status with styling"""
        if obj.is_primary:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Primary</span>'
            )
        return format_html('<span style="color: gray;">Secondary</span>')
    is_primary_display.short_description = 'Primary Status'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Customize foreign key fields in admin"""
        if db_field.name == "part":
            kwargs["queryset"] = Part.objects.order_by('part_number')
        elif db_field.name == "vendor":
            # Import here to avoid circular imports
            from vendors.models import Vendor
            kwargs["queryset"] = Vendor.objects.order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
