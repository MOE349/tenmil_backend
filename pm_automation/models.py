from django.db import models
from django.utils.translation import gettext_lazy as _
from configurations.base_features.db.base_model import BaseModel
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from tenant_users.models import TenantUser as User
from work_orders.models import WorkOrderChecklist
import logging

logger = logging.getLogger(__name__)


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
    
    # Trigger counter
    trigger_counter = models.PositiveIntegerField(default=0, help_text="Number of times this PM setting has been triggered")
    
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
        # Validate that interval_value is greater than 0
        if self.interval_value is not None and self.interval_value <= 0:
            raise ValueError("PM interval value must be greater than 0.")
        
        # Check if this is a new record or if key fields have changed
        old_interval_value = None
        if self.pk:  # This is an update
            try:
                # Get the original instance from database
                original = PMSettings.objects.get(pk=self.pk)
                old_interval_value = original.interval_value
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
        
        # Update all iterations to maintain their multiplier pattern
        if old_interval_value is not None and old_interval_value != self.interval_value:
            self.update_matching_iteration(old_interval_value)
    
    def update_matching_iteration(self, old_interval_value):
        """
        Update ALL iterations to maintain their multiplier pattern when PM interval changes.
        Each iteration represents a multiplier of the PM interval, so all iterations must be updated.
        """
        try:
            all_iterations = list(self.iterations.all().order_by('interval_value'))
            
            if not all_iterations:
                logger.info(f"No iterations to update for PM Settings {self.id}")
                return
            
            logger.info(f"Updating {len(all_iterations)} iterations for PM Settings {self.id}")
            logger.info(f"Old PM interval: {old_interval_value}, New PM interval: {self.interval_value}")
            
            # Choose update order based on interval change direction
            if old_interval_value > self.interval_value:
                # Going from higher to lower intervals (e.g., 1000 → 500)
                # Update in ASCENDING order (lowest first) to avoid conflicts
                update_order = all_iterations
                logger.info("Updating in ASCENDING order (higher to lower interval change)")
            else:
                # Going from lower to higher intervals (e.g., 500 → 1000)
                # Update in DESCENDING order (highest first) to avoid conflicts
                update_order = list(reversed(all_iterations))
                logger.info("Updating in DESCENDING order (lower to higher interval change)")
            
            updated_count = 0
            for iteration in update_order:
                try:
                    # Calculate the multiplier (iteration interval / old pm interval)
                    multiplier = iteration.interval_value / old_interval_value
                    
                    # Calculate new interval value with same multiplier
                    new_interval_value = self.interval_value * multiplier
                    
                    # Update the iteration to the new value based on its multiplier
                    old_name = iteration.name
                    iteration.interval_value = new_interval_value
                    iteration.name = f"{new_interval_value} {self.interval_unit}"
                    iteration.save()
                    
                    logger.info(f"Updated iteration {iteration.id}: {old_name} -> {iteration.name} (multiplier: {multiplier})")
                    updated_count += 1
                    
                except Exception as e:
                    logger.error(f"Error updating iteration {iteration.id}: {e}")
            
            logger.info(f"Successfully updated {updated_count} iterations for PM Settings {self.id}")
            
        except Exception as e:
            logger.error(f"Error updating iterations for PM Settings {self.id}: {e}")
    
    def update_other_iterations(self, old_interval_value, matching_iteration_id):
        """
        This method is no longer used - all iteration updates are handled in update_matching_iteration.
        Kept for backward compatibility but does nothing.
        """
        pass
    

    
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
    
    def get_iterations(self):
        """Get all iterations ordered by order field (interval_value / pm_interval)"""
        return self.iterations.all().order_by('order')
    
    def get_cumulative_checklist_for_iteration(self, iteration):
        """Get cumulative checklist for a specific iteration"""
        if not iteration:
            return []
        
        # Get all iterations up to and including the current one
        all_iterations = list(self.get_iterations())
        current_index = all_iterations.index(iteration)
        relevant_iterations = all_iterations[:current_index + 1]
        
        # Collect all checklist items from relevant iterations
        checklist_items = []
        for iter_item in relevant_iterations:
            checklist_items.extend(iter_item.checklist_items.all())
        
        return checklist_items
    
    def copy_iteration_checklist_to_work_order(self, work_order, iteration):
        """Copy cumulative checklist items for a specific iteration to work order"""
        checklist_items = self.get_cumulative_checklist_for_iteration(iteration)
        
        for item in checklist_items:
            WorkOrderChecklist.objects.create(
                work_order=work_order,
                description=item.name,
                source_pm_iteration_checklist=item
            )

    def get_iterations_for_trigger(self):
        """
        Get iterations that should be triggered based on the current counter.
        For each iteration, check if counter % order == 0.
        """
        iterations = list(self.get_iterations())
        triggered_iterations = []
        
        for iteration in iterations:
            if self.trigger_counter % iteration.order == 0:
                triggered_iterations.append(iteration)
        
        return triggered_iterations
    
    def increment_trigger_counter(self):
        """Increment the trigger counter by 1"""
        # Use update() to avoid triggering signals
        PMSettings.objects.filter(id=self.id).update(trigger_counter=self.trigger_counter + 1)
        # Refresh the instance to get the updated value
        self.refresh_from_db()
        return self.trigger_counter


class PMIteration(BaseModel):
    """PM Iteration - represents when a PM should occur based on interval"""
    pm_settings = models.ForeignKey(PMSettings, on_delete=models.CASCADE, related_name='iterations')
    interval_value = models.FloatField(_("Iteration Interval Value"), help_text="Interval value for this iteration")
    name = models.CharField(max_length=255, help_text="Iteration name (e.g., '500 Hours')")
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    
    class Meta:
        ordering = ['order']
        verbose_name = _("PM Iteration")
        verbose_name_plural = _("PM Iterations")
        unique_together = ['pm_settings', 'interval_value']
        indexes = [
            models.Index(fields=['pm_settings']),
            models.Index(fields=['pm_settings', 'interval_value']),
        ]
    
    def __str__(self):
        return f"{self.pm_settings} - {self.name}"
    
    def save(self, *args, **kwargs):
        # Validate that interval_value is greater than 0
        if self.interval_value is not None and self.interval_value <= 0:
            raise ValueError("Iteration interval value must be greater than 0.")
        
        # Validate that interval_value is a multiplier of the PM interval
        if self.pm_settings and self.interval_value:
            pm_interval = self.pm_settings.interval_value
            if self.interval_value % pm_interval != 0:
                raise ValueError(
                    f"Iteration interval value ({self.interval_value}) must be a multiplier of the PM interval ({pm_interval}). "
                    f"Valid values are: {pm_interval}, {pm_interval * 2}, {pm_interval * 3}, etc."
                )
            
            # Calculate order as interval_value / pm_interval
            self.order = int(self.interval_value / pm_interval)
        
        super().save(*args, **kwargs)


class PMIterationChecklist(BaseModel):
    """Checklist items for PM iterations"""
    iteration = models.ForeignKey(PMIteration, on_delete=models.CASCADE, related_name='checklist_items')
    name = models.CharField(max_length=255, help_text="Checklist item description")
    
    class Meta:
        verbose_name = _("PM Iteration Checklist")
        verbose_name_plural = _("PM Iteration Checklists")
        indexes = [
            models.Index(fields=['iteration']),
        ]
    
    def __str__(self):
        return f"{self.iteration} - {self.name}"


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




