from django.db import models
from django.utils.translation import gettext_lazy as _
from configurations.base_features.db.base_model import BaseModel
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from tenant_users.models import TenantUser as User
from work_orders.models import WorkOrderChecklist


class PMUnitChoices(models.TextChoices):
    """Available units for PM intervals and thresholds"""
    HOURS = 'hours', _('Hours')
    KILOMETERS = 'km', _('Kilometers')
    MILES = 'miles', _('Miles')
    CYCLES = 'cycles', _('Cycles')
    DAYS = 'days', _('Days')
    WEEKS = 'weeks', _('Weeks')
    MONTHS = 'months', _('Months')


class PMSettings(BaseModel):
    """PM Settings for an asset - defines when PM work orders should be created"""
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    asset = GenericForeignKey("content_type", "object_id")
    name = models.CharField(max_length=255, null=True, blank=True)
    
    # Interval settings - Every [value] [unit]
    interval_value = models.FloatField(_("Interval Value"), help_text="Every X units")
    interval_unit = models.CharField(
        _("Interval Unit"), 
        max_length=20, 
        choices=PMUnitChoices.choices,
        default=PMUnitChoices.HOURS
    )
    
    # Starting threshold - Starting at [value] [unit]
    start_threshold_value = models.FloatField(_("Starting Threshold Value"), help_text="Starting at X units")
    start_threshold_unit = models.CharField(
        _("Starting Threshold Unit"), 
        max_length=20, 
        choices=PMUnitChoices.choices,
        default=PMUnitChoices.HOURS
    )
    
    # Lead time settings - Create WO [value] [unit] before trigger
    lead_time_value = models.FloatField(_("Lead Time Value"), help_text="Create WO X units before trigger")
    lead_time_unit = models.CharField(
        _("Lead Time Unit"), 
        max_length=20, 
        choices=PMUnitChoices.choices,
        default=PMUnitChoices.HOURS
    )
    
    # Active status
    is_active = models.BooleanField(_("Active"), default=True, help_text="Enable/disable PM automation")
    
    # Next trigger tracking
    next_trigger_value = models.FloatField(_("Next Trigger Value"), null=True, blank=True)
    last_handled_trigger = models.FloatField(_("Last Handled Trigger"), null=True, blank=True)
    
    class Meta:
        verbose_name = _("PM Settings")
        verbose_name_plural = _("PM Settings")
    
    def __str__(self):
        try:
            asset_str = str(self.asset) if self.asset else f"{self.content_type.app_label}.{self.content_type.model}.{self.object_id}"
            return f"PM Settings for {asset_str} - Every {self.interval_value} {self.interval_unit}"
        except Exception:
            return f"PM Settings for {self.content_type.app_label}.{self.content_type.model}.{self.object_id} - Every {self.interval_value} {self.interval_unit}"
    
    def save(self, *args, **kwargs):
        # Check if this is a new record or if key fields have changed
        if self.pk:  # This is an update
            try:
                # Get the original instance from database
                original = PMSettings.objects.get(pk=self.pk)
                # Check if key fields that affect trigger calculation have changed
                if (original.start_threshold_value != self.start_threshold_value or 
                    original.interval_value != self.interval_value):
                    # Recalculate next trigger value
                    self.recalculate_next_trigger()
            except Exception:
                # This shouldn't happen, but if it does, just recalculate
                self.recalculate_next_trigger()
        else:  # This is a new record
            # Set initial next trigger on first save
            if not self.next_trigger_value:
                self.recalculate_next_trigger()
        
        super().save(*args, **kwargs)
    
    def recalculate_next_trigger(self):
        """Recalculate the next trigger value based on current settings"""
        if self.last_handled_trigger:
            # If we have a last handled trigger, use floating system
            # Next trigger = last handled + interval
            self.next_trigger_value = float(self.last_handled_trigger) + float(self.interval_value)
        else:
            # If no last handled trigger, use initial system
            # Next trigger = start threshold + interval
            self.next_trigger_value = float(self.start_threshold_value) + float(self.interval_value)
    
    def get_next_trigger(self):
        """Calculate the next trigger value"""
        if not self.next_trigger_value:
            # Initial trigger: start_threshold_value + interval_value
            return self.start_threshold_value + self.interval_value
        return self.next_trigger_value
    
    def update_next_trigger(self, closing_value):
        """Update next trigger after work order completion - Floating system"""
        # Floating trigger: completion_meter_reading + interval_value
        self.next_trigger_value = closing_value + self.interval_value
        self.last_handled_trigger = closing_value
        self.save()
    
    def get_checklist_items(self):
        """Get all checklist items for this PM setting"""
        return self.checklist_items.all()
    
    def add_checklist_item(self, name):
        """Add a checklist item to this PM setting"""
        return PMSettingsChecklist.objects.create(
            pm_settings=self,
            name=name
        )
    
    def copy_checklist_to_work_order(self, work_order):
        """Copy preset checklist items to a work order"""
        checklist_items = self.get_checklist_items()
        
        for item in checklist_items:
            WorkOrderChecklist.objects.create(
                work_order=work_order,
                description=item.name,
                source_pm_checklist=item
            )


class PMSettingsChecklist(BaseModel):
    """Preset checklist items for PM Settings"""
    pm_settings = models.ForeignKey(PMSettings, on_delete=models.CASCADE, related_name='checklist_items')
    name = models.CharField(max_length=255, help_text="Checklist item description")
    
    class Meta:
        verbose_name = _("PM Settings Checklist")
        verbose_name_plural = _("PM Settings Checklists")
        indexes = [
            models.Index(fields=['pm_settings']),
        ]
    
    def __str__(self):
        return f"{self.pm_settings} - {self.name}"


class PMTrigger(BaseModel):
    """Tracks PM triggers and their associated work orders"""
    pm_settings = models.ForeignKey(PMSettings, on_delete=models.CASCADE, related_name='triggers')
    trigger_value = models.FloatField(_("Trigger Value"))
    trigger_unit = models.CharField(_("Trigger Unit"), max_length=20, choices=PMUnitChoices.choices)
    work_order = models.ForeignKey('work_orders.WorkOrder', on_delete=models.CASCADE, null=True, blank=True)
    is_handled = models.BooleanField(_("Is Handled"), default=False)
    handled_at = models.DateTimeField(_("Handled At"), null=True, blank=True)
    
    class Meta:
        unique_together = ['pm_settings', 'trigger_value']
        verbose_name = _("PM Trigger")
        verbose_name_plural = _("PM Triggers")
    
    def __str__(self):
        try:
            asset_str = str(self.pm_settings.asset) if self.pm_settings.asset else f"{self.pm_settings.content_type.app_label}.{self.pm_settings.content_type.model}.{self.pm_settings.object_id}"
            return f"PM Trigger at {self.trigger_value} {self.trigger_unit} for {asset_str}"
        except Exception:
            return f"PM Trigger at {self.trigger_value} {self.trigger_unit} for {self.pm_settings.content_type.app_label}.{self.pm_settings.content_type.model}.{self.pm_settings.object_id}"




