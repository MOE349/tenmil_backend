from django.db import models
from django.utils.translation import gettext_lazy as _
from configurations.base_features.db.base_model import BaseModel
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
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
    YEARS = 'years', _('Years')


class PMTriggerTypes(models.TextChoices):
    """Types of PM triggers"""
    METER_READING = 'METER', _('Meter Reading')
    CALENDAR = 'CALENDAR', _('Calendar Based')


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
    start_threshold_value = models.FloatField(_("Starting Threshold Value"), help_text="Starting at X units", null=True, 
        blank=True,)
    
    # Lead time settings - Create WO [value] [unit] before trigger
    lead_time_value = models.FloatField(_("Lead Time Value"), help_text="Create WO X units before trigger", null=True, 
        blank=True,)
    
    # Active status
    is_active = models.BooleanField(_("Active"), default=True, help_text="Enable/disable PM automation")
    
    # Next trigger tracking
    next_trigger_value = models.FloatField(_("Next Trigger Value"), null=True, blank=True)
    last_handled_trigger = models.FloatField(_("Last Handled Trigger"), null=True, blank=True)
    
    # Trigger counter
    trigger_counter = models.PositiveIntegerField(default=0, help_text="Number of times this PM setting has been triggered")
    
    # NEW: Trigger type
    trigger_type = models.CharField(
        _("Trigger Type"),
        max_length=20,
        choices=PMTriggerTypes.choices,
        default=PMTriggerTypes.METER_READING
    )
    
    # NEW: Calendar-specific fields
    start_date = models.DateTimeField(
        _("Start Date"), 
        null=True, 
        blank=True,
        help_text=_("Start date for calendar-based PMs")
    )
    next_due_date = models.DateTimeField(
        _("Next Due Date"), 
        null=True, 
        blank=True,
        help_text=_("Calculated next due date for calendar PMs")
    )
    last_completion_date = models.DateTimeField(
        _("Last Completion Date"), 
        null=True, 
        blank=True,
        help_text=_("Date of last work order completion")
    )
    
    # NEW: Lead time for calendar PMs (create WO X days before due)
    calendar_lead_time_days = models.PositiveIntegerField(
        _("Calendar Lead Time (Days)"),
        default=0,
        help_text=_("Create work order X days before due date (calendar PMs only)")
    )
    
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
        
        # Normalize calendar PM dates to start of day (00:00:00)
        if self.trigger_type == PMTriggerTypes.CALENDAR:
            if self.start_date:
                self.start_date = self.start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            if self.next_due_date:
                self.next_due_date = self.next_due_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Check if this is a new record or if key fields have changed
        old_interval_value = None
        if self.pk:  # This is an update
            try:
                # Get the original instance from database
                original = PMSettings.objects.get(pk=self.pk)
                old_interval_value = original.interval_value
                # Check if key fields that affect trigger calculation have changed
                if self.trigger_type == PMTriggerTypes.METER_READING:
                    if (original.start_threshold_value != self.start_threshold_value or 
                        original.interval_value != self.interval_value or
                        original.trigger_type != self.trigger_type):
                        # Recalculate next trigger value for meter PMs
                        self.recalculate_next_trigger()
                elif self.trigger_type == PMTriggerTypes.CALENDAR:
                    if (original.start_date != self.start_date or
                        original.interval_value != self.interval_value or
                        original.trigger_type != self.trigger_type):
                        # Recalculate next due date for calendar PMs
                        self.next_due_date = self.calculate_next_calendar_due_date()
            except Exception:
                # This shouldn't happen, but if it does, just recalculate based on type
                if self.trigger_type == PMTriggerTypes.METER_READING:
                    self.recalculate_next_trigger()
                elif self.trigger_type == PMTriggerTypes.CALENDAR:
                    self.next_due_date = self.calculate_next_calendar_due_date()
        else:  # This is a new record
            # Set initial trigger/due date on first save
            if self.trigger_type == PMTriggerTypes.METER_READING:
                if not self.next_trigger_value:
                    self.recalculate_next_trigger()
            elif self.trigger_type == PMTriggerTypes.CALENDAR:
                if not self.next_due_date:
                    self.next_due_date = self.calculate_next_calendar_due_date()
        
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
        """Recalculate the next trigger value based on current settings (meter PMs only)"""
        # Only calculate for meter-based PMs
        if self.trigger_type != PMTriggerTypes.METER_READING:
            return
        
        if self.last_handled_trigger:
            # If we have a last handled trigger, use floating system
            # Next trigger = last handled + interval
            self.next_trigger_value = float(self.last_handled_trigger) + float(self.interval_value)
        elif self.start_threshold_value is not None:
            # If no last handled trigger, use initial system
            # Next trigger = start threshold + interval
            self.next_trigger_value = float(self.start_threshold_value) + float(self.interval_value)
        else:
            # No start threshold set - this is likely an incomplete meter PM
            logger.warning(f"PM Settings {self.id}: Cannot calculate next trigger - start_threshold_value is None")
            self.next_trigger_value = None
    
    def get_next_trigger(self):
        """Calculate the next trigger value (meter PMs only)"""
        if self.trigger_type != PMTriggerTypes.METER_READING:
            return None
        
        if not self.next_trigger_value:
            # Initial trigger: start_threshold_value + interval_value
            if self.start_threshold_value is not None:
                return self.start_threshold_value + self.interval_value
            else:
                return None
        return self.next_trigger_value
    
    def update_next_trigger(self, closing_value):
        """Update next trigger after work order completion - Floating system"""
        # NOTE: Don't increment trigger_counter here - it's already incremented during work order creation
        
        # Calculate the next trigger interval based on what iteration will trigger next
        # Use current counter + 1 to find the next trigger
        next_counter = self.trigger_counter + 1
        iterations = list(self.get_iterations())
        
        # Find the iteration that will trigger at the next counter
        next_trigger_interval = self.interval_value  # Default to base interval
        for iteration in iterations:
            if next_counter % iteration.order == 0:
                next_trigger_interval = iteration.interval_value
                break
        
        # Floating trigger: completion_meter_reading + next_trigger_interval
        self.next_trigger_value = closing_value + next_trigger_interval
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
    
    def get_asset_timezone(self):
        """Get timezone for the asset this PM is attached to"""
        try:
            # Assuming asset has a site relationship
            asset = self.asset
            if hasattr(asset, 'site') and asset.site:
                return asset.site.get_effective_timezone()
            elif hasattr(asset, 'location') and asset.location and asset.location.site:
                return asset.location.site.get_effective_timezone()
            
            # Fallback to company timezone
            from company.models import CompanyProfile
            company_profile = CompanyProfile.get_or_create_default()
            return company_profile.get_timezone_object()
        except:
            # Final fallback to UTC
            import pytz
            return pytz.UTC
    
    def calculate_next_calendar_due_date(self, from_date=None):
        """Calculate next due date for calendar-based PMs"""
        if self.trigger_type != PMTriggerTypes.CALENDAR:
            return None
        
        # Use provided date, last completion, or start date
        base_date = from_date or self.last_completion_date or self.start_date
        
        if not base_date:
            return None
        
        # Ensure base_date is timezone-aware
        asset_tz = self.get_asset_timezone()
        if base_date.tzinfo is None:
            base_date = asset_tz.localize(base_date)
        
        # Normalize base_date to start of day (00:00:00)
        base_date = base_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate next due date based on interval
        from dateutil.relativedelta import relativedelta
        from datetime import timedelta
        
        if self.interval_unit == PMUnitChoices.DAYS:
            next_due = base_date + timedelta(days=int(self.interval_value))
        elif self.interval_unit == PMUnitChoices.WEEKS:
            next_due = base_date + timedelta(weeks=int(self.interval_value))
        elif self.interval_unit == PMUnitChoices.MONTHS:
            next_due = base_date + relativedelta(months=int(self.interval_value))
        elif self.interval_unit == PMUnitChoices.YEARS:
            next_due = base_date + relativedelta(years=int(self.interval_value))
        else:
            return None
        
        # Ensure next due date is also normalized to start of day
        return next_due.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def update_calendar_due_date(self, completion_date=None):
        """Update next due date after work order completion"""
        if self.trigger_type == PMTriggerTypes.CALENDAR:
            from django.utils import timezone
            
            completion_dt = completion_date or timezone.now()
            asset_tz = self.get_asset_timezone()
            
            # Ensure timezone awareness
            if completion_dt.tzinfo is None:
                completion_dt = asset_tz.localize(completion_dt)
            
            self.last_completion_date = completion_dt
            self.next_due_date = self.calculate_next_calendar_due_date()
            self.save(update_fields=['last_completion_date', 'next_due_date'])
    
    def is_calendar_pm_due(self, check_lead_time=True):
        """Check if calendar PM is due (considering lead time)"""
        if self.trigger_type != PMTriggerTypes.CALENDAR or not self.next_due_date:
            return False
        
        from django.utils import timezone
        current_time = timezone.now()
        
        if check_lead_time and self.calendar_lead_time_days > 0:
            # Check if we're within lead time window
            from datetime import timedelta
            lead_time_threshold = self.next_due_date - timedelta(days=self.calendar_lead_time_days)
            return current_time >= lead_time_threshold
        else:
            # Check if actually due
            return current_time >= self.next_due_date
    



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




