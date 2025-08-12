from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from pm_automation.models import PMSettings, PMTrigger, PMTriggerTypes
from work_orders.models import WorkOrder, WorkOrderStatusNames, WorkOrderLog
from tenant_users.models import TenantUser
import logging

logger = logging.getLogger(__name__)


class CalendarPMService:
    """Service for handling calendar-based PM automation"""
    
    @staticmethod
    def check_calendar_pms_due():
        """Check for calendar-based PMs that are due (Celery task)"""
        current_datetime = timezone.now()
        
        # Get all active calendar PMs that are due (including lead time)
        due_pms = PMSettings.objects.filter(
            trigger_type=PMTriggerTypes.CALENDAR,
            is_active=True
        ).exclude(
            # Exclude if already has open PM work order
            object_id__in=WorkOrder.objects.filter(
                is_pm_generated=True,  # Use is_pm_generated flag instead of maint_type
                is_closed=False
            ).values_list('object_id', flat=True)
        )
        
        # Filter to only those that are actually due
        actually_due_pms = []
        for pm_settings in due_pms:
            if pm_settings.is_calendar_pm_due(check_lead_time=True):
                actually_due_pms.append(pm_settings)
        
        logger.info(f"Found {len(actually_due_pms)} calendar PMs that are due")
        
        created_work_orders = []
        for pm_settings in actually_due_pms:
            work_order = CalendarPMService._create_calendar_work_order(pm_settings)
            if work_order:
                created_work_orders.append(work_order)
        
        return created_work_orders
    
    @staticmethod
    def _create_calendar_work_order(pm_settings):
        """Create work order for calendar-based PM"""
        try:
            # Increment the trigger counter (like meter PMs)
            new_counter = pm_settings.increment_trigger_counter()
            
            # Calculate triggered iterations using the new counter (like meter PMs)
            triggered_iterations = []
            for iteration in pm_settings.get_iterations():
                if new_counter % iteration.order == 0:
                    triggered_iterations.append(iteration)
            
            logger.info(f"Calendar PM counter {new_counter} triggers iterations: {[f'{it.interval_value}{pm_settings.interval_unit}(order:{it.order})' for it in triggered_iterations]}")
            
            # Create description (matching meter PM format)
            if triggered_iterations:
                # Use the largest (highest interval) triggered iteration for description
                largest_iteration = max(triggered_iterations, key=lambda x: x.interval_value)
                iteration_value = int(largest_iteration.interval_value)
                unit_formatted = pm_settings.interval_unit
                
                # Use PM settings name if available
                if pm_settings.name:
                    description = f"{pm_settings.name} {iteration_value} {unit_formatted}"
                else:
                    # Fallback to generic PM naming
                    description = f"{iteration_value} {unit_formatted} PM"
            else:
                # Fallback if no iterations (shouldn't happen normally)
                iteration_value = int(pm_settings.interval_value)
                unit_formatted = pm_settings.interval_unit
                if pm_settings.name:
                    description = f"{pm_settings.name} {iteration_value} {unit_formatted}"
                else:
                    description = f"{iteration_value} {unit_formatted} PM"
            
            # Get system admin user
            system_admin = TenantUser.objects.filter(
                is_superuser=True
            ).order_by('created_at').first()
            
            if not system_admin:
                logger.error("No system admin found for work order creation")
                return None
            
            # Get active status
            try:
                # Try to get a status with preferred names first
                active_status = (
                    WorkOrderStatusNames.objects.filter(name__iexact='Active').first() or
                    WorkOrderStatusNames.objects.filter(name__iexact='Draft').first() or
                    WorkOrderStatusNames.objects.filter(name__iexact='Pending').first() or
                    WorkOrderStatusNames.objects.first()
                )
            except:
                active_status = None
            
            # Create work order
            work_order = WorkOrder.objects.create(
                content_type=pm_settings.content_type,
                object_id=pm_settings.object_id,
                status=active_status,
                maint_type=pm_settings.maint_type,  ,
                description=description,
                is_pm_generated=True,
                # Note: No trigger_meter_reading for calendar PMs
            )
            
            logger.info(f"Created calendar PM work order {work_order.id}: {work_order.description}")
            
            # Create PM trigger record
            PMTrigger.objects.create(
                pm_settings=pm_settings,
                work_order=work_order,
                trigger_value=new_counter,  # Use the incremented counter for uniqueness
                trigger_unit=pm_settings.interval_unit,  # Use the PM interval unit
            )
            
            # Copy iteration checklists (matching meter PM logic)
            try:
                if triggered_iterations:
                    # Get the highest-order iteration (which will have the most comprehensive checklist)
                    highest_order_iteration = max(triggered_iterations, key=lambda x: x.order)
                    
                    # Copy the cumulative checklist for the highest-order iteration
                    pm_settings.copy_iteration_checklist_to_work_order(work_order, highest_order_iteration)
                    logger.info(f"Copied cumulative checklist for highest-order iteration '{highest_order_iteration.name}' to work order {work_order.id}")
            except Exception as e:
                logger.error(f"Error copying iteration checklists to work order {work_order.id}: {e}")
            
            # Log creation (matching meter PM format)
            WorkOrderLog.objects.create(
                work_order=work_order,
                amount=0,
                log_type=WorkOrderLog.LogTypeChoices.CREATED,
                user=system_admin,
                description="Work Order Created (Calendar PM Automation)"
            )
            
            logger.info(f"Created work order log for work order {work_order.id}")
            
            # Update next due date
            pm_settings.next_due_date = pm_settings.calculate_next_calendar_due_date()
            pm_settings.save(update_fields=['next_due_date'])
            
            logger.info(f"Updated PM settings: counter={pm_settings.trigger_counter}, next_due={pm_settings.next_due_date}")
            
            return work_order
            
        except Exception as e:
            logger.error(f"Error creating calendar PM work order for PM {pm_settings.id}: {e}")
            return None
    
    @staticmethod
    def handle_calendar_work_order_completion(work_order):
        """Handle calendar PM work order completion"""
        try:
            # Find the PM trigger for this work order
            pm_trigger = PMTrigger.objects.filter(work_order=work_order).first()
            if not pm_trigger:
                logger.warning(f"No PM trigger found for work order {work_order.id}")
                return
            
            # Update the trigger as handled
            pm_trigger.is_handled = True
            pm_trigger.handled_at = timezone.now()
            pm_trigger.save()
            
            logger.info(f"Updated PM trigger {pm_trigger.id} as handled")
            
            # Update PM settings with completion date
            pm_settings = pm_trigger.pm_settings
            if pm_settings.trigger_type == PMTriggerTypes.CALENDAR:
                # Use work order completion_end_date if available, otherwise current time
                completion_date = None
                if work_order.completion_end_date:
                    # Convert date to datetime for consistency
                    completion_date = timezone.datetime.combine(
                        work_order.completion_end_date, 
                        timezone.datetime.min.time()
                    ).replace(tzinfo=timezone.get_current_timezone())
                else:
                    completion_date = timezone.now()
                
                # Update last completion date and calculate next due date based on actual completion
                pm_settings.last_completion_date = completion_date
                pm_settings.next_due_date = pm_settings.calculate_next_calendar_due_date()
                pm_settings.save(update_fields=['last_completion_date', 'next_due_date'])
                
                logger.info(f"Updated calendar PM: last_completion={pm_settings.last_completion_date}, next_due={pm_settings.next_due_date} (based on completion_end_date: {work_order.completion_end_date})")
                
        except Exception as e:
            logger.error(f"Error handling calendar PM work order completion for {work_order.id}: {e}")
