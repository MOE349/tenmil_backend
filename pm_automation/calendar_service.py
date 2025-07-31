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
                maint_type='PM',
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
            # Get triggered iterations
            triggered_iterations = pm_settings.get_calendar_triggered_iterations()
            
            # Create description
            iterations_text = ", ".join([iter.name for iter in triggered_iterations]) if triggered_iterations else "Base PM"
            description = f"PM: {pm_settings.name or 'Scheduled Maintenance'} - Every {pm_settings.interval_value} {pm_settings.interval_unit} ({iterations_text})"
            
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
                maint_type='PM',
                priority='medium',
                description=description,
                is_pm_generated=True,
                # Note: No trigger_meter_reading for calendar PMs
            )
            
            logger.info(f"Created calendar PM work order {work_order.id}: {work_order.description}")
            
            # Create PM trigger record
            PMTrigger.objects.create(
                pm_settings=pm_settings,
                work_order=work_order,
                trigger_value=0,  # Not applicable for calendar PMs
                trigger_unit=pm_settings.interval_unit,  # Use the PM interval unit
            )
            
            # Copy iteration checklists
            try:
                if triggered_iterations:
                    highest_order_iteration = max(triggered_iterations, key=lambda x: x.order)
                    pm_settings.copy_iteration_checklist_to_work_order(work_order, highest_order_iteration)
                    logger.info(f"Copied checklist for iteration '{highest_order_iteration.name}' to work order {work_order.id}")
            except Exception as e:
                logger.error(f"Error copying iteration checklists to work order {work_order.id}: {e}")
            
            # Log creation
            try:
                WorkOrderLog.objects.create(
                    work_order=work_order,
                    amount=0,
                    log_type=WorkOrderLog.LogTypeChoices.CREATED,
                    user=system_admin,
                    description="Work Order Created (Calendar PM Automation)"
                )
            except Exception as e:
                logger.error(f"Error creating work order log: {e}")
            
            # Update trigger counter and next due date
            pm_settings.trigger_counter += 1
            pm_settings.next_due_date = pm_settings.calculate_next_calendar_due_date()
            pm_settings.save(update_fields=['trigger_counter', 'next_due_date'])
            
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
                pm_settings.update_calendar_due_date(timezone.now())
                logger.info(f"Updated calendar PM next due date to {pm_settings.next_due_date}")
                
        except Exception as e:
            logger.error(f"Error handling calendar PM work order completion for {work_order.id}: {e}")
