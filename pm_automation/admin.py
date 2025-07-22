from django.contrib import admin
from pm_automation.models import PMSettings, PMTrigger, PMSettingsChecklist, PMUnitChoices


class PMSettingsChecklistInline(admin.TabularInline):
    model = PMSettingsChecklist
    extra = 1
    fields = ['name']


@admin.register(PMSettings)
class PMSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'content_type', 'object_id', 'interval_value', 'interval_unit', 'start_threshold_value', 'start_threshold_unit', 'lead_time_value', 'lead_time_unit', 'is_active', 'next_trigger_value')
    list_filter = ('is_active', 'interval_unit', 'start_threshold_unit', 'lead_time_unit')
    search_fields = ('content_type__app_label', 'content_type__model', 'object_id')
    readonly_fields = ('next_trigger_value', 'last_handled_trigger')
    inlines = [PMSettingsChecklistInline]
    
    fieldsets = (
        ('Asset', {
            'fields': ('content_type', 'object_id')
        }),
        ('Interval Settings', {
            'fields': ('interval_value', 'interval_unit')
        }),
        ('Starting Threshold', {
            'fields': ('start_threshold_value', 'start_threshold_unit'),
            'description': 'Initial trigger = start_threshold_value + interval_value'
        }),
        ('Lead Time Settings', {
            'fields': ('lead_time_value', 'lead_time_unit')
        }),
        ('Floating Trigger Status', {
            'fields': ('is_active', 'next_trigger_value', 'last_handled_trigger'),
            'description': 'Next trigger = completion_meter_reading + interval_value'
        }),
    )


@admin.register(PMTrigger)
class PMTriggerAdmin(admin.ModelAdmin):
    list_display = ('id', 'pm_settings', 'trigger_value', 'trigger_unit', 'work_order', 'is_handled', 'handled_at')
    list_filter = ('is_handled', 'trigger_unit', 'handled_at')
    search_fields = ('pm_settings__content_type__app_label', 'pm_settings__content_type__model', 'pm_settings__object_id')
    readonly_fields = ('handled_at',)
    
    fieldsets = (
        ('PM Settings', {
            'fields': ('pm_settings',)
        }),
        ('Trigger', {
            'fields': ('trigger_value', 'trigger_unit')
        }),
        ('Work Order', {
            'fields': ('work_order',)
        }),
        ('Status', {
            'fields': ('is_handled', 'handled_at')
        }),
    )


@admin.register(PMSettingsChecklist)
class PMSettingsChecklistAdmin(admin.ModelAdmin):
    list_display = ['name', 'pm_settings']
    list_filter = ['pm_settings']
    search_fields = ['name', 'pm_settings__name']
