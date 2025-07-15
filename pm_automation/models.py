from django.db import models
from django.utils.translation import gettext_lazy as _
from configurations.base_features.db.base_model import BaseModel
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from tenant_users.models import TenantUser as User


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
        # Allow multiple PM settings per asset by making name part of unique constraint
        unique_together = [['content_type', 'object_id', 'name']]
    
    def __str__(self):
        try:
            asset_str = str(self.asset) if self.asset else f"{self.content_type.app_label}.{self.content_type.model}.{self.object_id}"
            return f"PM Settings for {asset_str} - Every {self.interval_value} {self.interval_unit}"
        except Exception:
            return f"PM Settings for {self.content_type.app_label}.{self.content_type.model}.{self.object_id} - Every {self.interval_value} {self.interval_unit}"
    
    def save(self, *args, **kwargs):
        # Set initial next trigger on first save
        if not self.next_trigger_value:
            # Initial trigger: start_threshold_value + interval_value
            self.next_trigger_value = self.start_threshold_value + self.interval_value
        super().save(*args, **kwargs)
    
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




