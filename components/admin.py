from components.models import *
from django.contrib import admin


@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    list_display = ['name', 'work_order', 'initial_meter_reading', 'warranty_meter_reading', 'warranty_exp_date', 'is_warranty_expired', 'created_at']
    list_filter = ['is_warranty_expired', 'warranty_exp_date', 'created_at']
    search_fields = ['name', 'work_order__code']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'work_order', 'initial_meter_reading')
        }),
        ('Asset Information', {
            'fields': ('content_type', 'object_id')
        }),
        ('Warranty Information', {
            'fields': ('warranty_meter_reading', 'warranty_exp_date', 'is_warranty_expired')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
