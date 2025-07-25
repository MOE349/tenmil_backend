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
    
    # Current iteration tracking
    current_iteration_index = models.PositiveIntegerField(default=0, help_text="Index of current iteration in the cycle")
    
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
        
        # Update the iteration that matches the old interval value
        if old_interval_value is not None and old_interval_value != self.interval_value:
            self.update_matching_iteration(old_interval_value)
    
    def update_matching_iteration(self, old_interval_value):
        """
        Update the iteration that matches the old interval value to match the new interval value.
        Only updates the iteration that exactly matches the old PM settings interval value.
        """
        try:
            # Find the iteration that matches the old interval value
            matching_iteration = self.iterations.filter(interval_value=old_interval_value).first()
            
            if matching_iteration:
                # Store the matching iteration ID before updating it
                matching_iteration_id = matching_iteration.id
                
                # Check if there's already an iteration with the new interval value
                existing_iteration_with_new_value = self.iterations.filter(interval_value=self.interval_value).exclude(id=matching_iteration.id).first()
                
                if existing_iteration_with_new_value:
                    # If there's already an iteration with the new value, delete the matching iteration
                    # and keep the existing one (don't mark it as matching_iteration_id)
                    logger.info(f"Found existing iteration {existing_iteration_with_new_value.id} with new interval value {self.interval_value}")
                    logger.info(f"Deleting matching iteration {matching_iteration.id} and keeping existing iteration")
                    matching_iteration.delete()
                    matching_iteration_id = None  # Don't exclude the existing iteration from updates
                else:
                    # Update the iteration to match the new interval value
                    old_name = matching_iteration.name
                    matching_iteration.interval_value = self.interval_value
                    matching_iteration.name = f"{self.interval_value} {self.interval_unit}"
                    matching_iteration.save()
                    
                    logger.info(f"Updated iteration {matching_iteration.id}: {old_name} -> {matching_iteration.name}")
            else:
                logger.info(f"No iteration found matching old interval value {old_interval_value} for PM Settings {self.id}")
                matching_iteration_id = None
            
            # Second action: Update all other iterations based on their multipliers
            self.update_other_iterations(old_interval_value, matching_iteration_id)
                
        except Exception as e:
            logger.error(f"Error updating matching iteration for PM Settings {self.id}: {e}")
    
    def update_other_iterations(self, old_interval_value, matching_iteration_id):
        """
        Update all other iterations by calculating their multiplier and applying it to the new interval.
        This is the second action, separate from updating the matching iteration.
        """
        try:
            # Get all iterations except the one that was just updated (using ID instead of interval_value)
            if matching_iteration_id:
                other_iterations = self.iterations.exclude(id=matching_iteration_id)
            else:
                # If no matching iteration was found, get all iterations
                other_iterations = self.iterations.all()
            
            if not other_iterations.exists():
                logger.info(f"No other iterations to update for PM Settings {self.id}")
                return
            
            logger.info(f"Updating {other_iterations.count()} other iterations for PM Settings {self.id}")
            
            updated_count = 0
            for iteration in other_iterations:
                try:
                    # Skip iterations that already match the new PM interval value
                    if iteration.interval_value == self.interval_value:
                        logger.info(f"Skipping iteration {iteration.id} with value {iteration.interval_value} (already matches new PM interval)")
                        continue
                    
                    # Calculate the multiplier (iteration interval / old pm interval)
                    multiplier = iteration.interval_value / old_interval_value
                    
                    # Calculate new interval value with same multiplier
                    new_interval_value = self.interval_value * multiplier
                    
                    # Update the iteration to the new value based on its multiplier
                    old_name = iteration.name
                    iteration.interval_value = new_interval_value
                    iteration.name = f"{new_interval_value} {self.interval_unit}"
                    iteration.save()
                    
                    logger.info(f"Updated other iteration {iteration.id}: {old_name} -> {iteration.name} (multiplier: {multiplier})")
                    updated_count += 1
                    
                except Exception as e:
                    logger.error(f"Error updating other iteration {iteration.id}: {e}")
            
            logger.info(f"Successfully updated {updated_count} other iterations for PM Settings {self.id}")
            
        except Exception as e:
            logger.error(f"Error updating other iterations for PM Settings {self.id}: {e}")
    

    
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
        """Get all iterations ordered by interval value"""
        return self.iterations.all().order_by('interval_value')
    
    def get_current_iteration(self):
        """Get the current iteration based on current_iteration_index"""
        iterations = list(self.get_iterations())
        if not iterations:
            return None
        return iterations[self.current_iteration_index % len(iterations)]
    
    def advance_to_next_iteration(self):
        """Advance to the next iteration in the cycle"""
        iterations = list(self.get_iterations())
        if not iterations:
            return None
        
        self.current_iteration_index = (self.current_iteration_index + 1) % len(iterations)
        self.save()
        return self.get_current_iteration()
    
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

    def get_iteration_for_trigger(self, trigger_value):
        """
        Return the PMIteration whose interval_value is the largest divisor of trigger_value,
        and is a defined iteration for this PMSettings.
        """
        iterations = list(self.get_iterations())
        valid_iterations = [it for it in iterations if trigger_value % it.interval_value == 0]
        if not valid_iterations:
            return None
        # Return the iteration with the largest interval_value
        return max(valid_iterations, key=lambda it: it.interval_value)


class PMIteration(BaseModel):
    """PM Iteration - represents when a PM should occur based on interval"""
    pm_settings = models.ForeignKey(PMSettings, on_delete=models.CASCADE, related_name='iterations')
    interval_value = models.FloatField(_("Iteration Interval Value"), help_text="Interval value for this iteration")
    name = models.CharField(max_length=255, help_text="Iteration name (e.g., '500 Hours')")
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    
    class Meta:
        ordering = ['interval_value']
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
        # Auto-assign order if not provided
        if not self.order:
            max_order = PMIteration.objects.filter(pm_settings=self.pm_settings).aggregate(
                max_order=models.Max('order')
            )['max_order'] or 0
            self.order = max_order + 1
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




