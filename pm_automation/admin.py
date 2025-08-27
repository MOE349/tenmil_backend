from django.contrib import admin
from pm_automation.models import PMSettings, PMTrigger, PMIteration, PMIterationChecklist, PMIterationParts


class PMIterationChecklistInline(admin.TabularInline):
    model = PMIterationChecklist
    extra = 1
    fields = ['name']


class PMIterationPartsInline(admin.TabularInline):
    model = PMIterationParts
    extra = 1
    fields = ['part', 'qty_needed']
    autocomplete_fields = ['part']


class PMIterationInline(admin.TabularInline):
    model = PMIteration
    extra = 1
    fields = ['interval_value', 'name', 'order']
    readonly_fields = ['order']
    inlines = [PMIterationChecklistInline]


@admin.register(PMSettings)
class PMSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'content_type', 'object_id', 'interval_value', 'interval_unit', 'start_threshold_value', 'interval_unit', 'lead_time_value', 'is_active', 'next_trigger_value', 'trigger_counter', 'iterations_count')
    list_filter = ('is_active', 'interval_unit')
    search_fields = ('content_type__app_label', 'content_type__model', 'object_id')
    readonly_fields = ('next_trigger_value', 'last_handled_trigger', 'trigger_counter', 'iterations_count')
    inlines = [PMIterationInline]
    
    def iterations_count(self, obj):
        """Show the number of iterations for this PM settings"""
        return obj.iterations.count()
    iterations_count.short_description = 'Iterations'
    
    fieldsets = (
        ('Asset', {
            'fields': ('content_type', 'object_id')
        }),
        ('Interval Settings', {
            'fields': ('interval_value', 'interval_unit')
        }),
        ('Starting Threshold', {
            'fields': ('start_threshold_value',),
            'description': 'Initial trigger = start_threshold_value + interval_value'
        }),
        ('Lead Time Settings', {
            'fields': ('lead_time_value',)
        }),
        ('Floating Trigger Status', {
            'fields': ('is_active', 'next_trigger_value', 'last_handled_trigger', 'trigger_counter'),
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


@admin.register(PMIteration)
class PMIterationAdmin(admin.ModelAdmin):
    list_display = ['name', 'pm_settings', 'interval_value', 'order', 'is_default_iteration', 'multiplier']
    list_filter = ['pm_settings']
    search_fields = ['name', 'pm_settings__name']
    ordering = ['pm_settings', 'interval_value']
    inlines = [PMIterationChecklistInline, PMIterationPartsInline]
    readonly_fields = ['is_default_iteration', 'multiplier']
    
    def multiplier(self, obj):
        """Show the multiplier for this iteration (how many times the base interval)"""
        if obj.pm_settings.interval_value > 0:
            return f"{obj.interval_value / obj.pm_settings.interval_value:.1f}x"
        return "N/A"
    multiplier.short_description = 'Multiplier'
    
    def is_default_iteration(self, obj):
        """Check if this iteration matches the PM settings' interval_value"""
        return obj.interval_value == obj.pm_settings.interval_value
    is_default_iteration.boolean = True
    is_default_iteration.short_description = 'Default Iteration'
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of default iterations"""
        if obj and obj.interval_value == obj.pm_settings.interval_value:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(PMIterationChecklist)
class PMIterationChecklistAdmin(admin.ModelAdmin):
    list_display = ['name', 'iteration', 'iteration_pm_settings']
    list_filter = ['iteration__pm_settings']
    search_fields = ['name', 'iteration__name']
    
    def iteration_pm_settings(self, obj):
        return obj.iteration.pm_settings
    iteration_pm_settings.short_description = 'PM Settings'


@admin.register(PMIterationParts)
class PMIterationPartsAdmin(admin.ModelAdmin):
    list_display = ['part_number', 'part_name', 'qty_needed', 'iteration', 'iteration_pm_settings', 'estimated_cost']
    list_filter = ['iteration__pm_settings', 'part']
    search_fields = ['part__part_number', 'part__name', 'iteration__name']
    autocomplete_fields = ['part']
    
    def part_number(self, obj):
        return obj.part.part_number if obj.part else 'N/A'
    part_number.short_description = 'Part Number'
    
    def part_name(self, obj):
        return obj.part.name if obj.part else 'N/A'
    part_name.short_description = 'Part Name'
    
    def iteration_pm_settings(self, obj):
        return obj.iteration.pm_settings
    iteration_pm_settings.short_description = 'PM Settings'
    
    def estimated_cost(self, obj):
        if obj.part and obj.part.last_price:
            return f"${obj.part.last_price * obj.qty_needed:.2f}"
        return 'N/A'
    estimated_cost.short_description = 'Estimated Cost'
