from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from meter_readings.models import MeterReading
from pm_automation.models import PMSettings, PMTrigger, PMUnitChoices
from work_orders.models import WorkOrder, WorkOrderStatusNames, WorkOrderLog
from tenant_users.models import TenantUser
from assets.services import get_content_type_and_asset_id
import logging

# Set up logging
logger = logging.getLogger(__name__)


class PMAutomationService:
    """Service for handling meter-driven PM automation"""
    
    @staticmethod
    def process_meter_reading(asset_id, meter_reading_value, meter_reading_unit, user):
        """
        Process a new meter reading and check for PM triggers
        
        Args:
            asset_id: The asset ID
            meter_reading_value: The meter reading value
            meter_reading_unit: The meter reading unit
            user: The user who created the meter reading
        """
        logger.info(f"Processing meter reading for asset {asset_id}: {meter_reading_value} {meter_reading_unit}")
        
        # Get active PM settings for this asset
        pm_settings_list = PMAutomationService._get_active_pm_settings(asset_id)
        if not pm_settings_list.exists():
            logger.info(f"No active PM settings found for asset {asset_id}")
            return None
        
        logger.info(f"Found {pm_settings_list.count()} active PM settings for asset {asset_id}")
        
        # Process each PM setting
        all_created_work_orders = []
        for pm_settings in pm_settings_list:
            logger.info(f"Processing PM Settings ID {pm_settings.id}: interval={pm_settings.interval_value} {pm_settings.interval_unit}, start_threshold={pm_settings.start_threshold_value} {pm_settings.start_threshold_unit}, lead_time={pm_settings.lead_time_value} {pm_settings.lead_time_unit}")
            
            # Check if units match
            if pm_settings.interval_unit != meter_reading_unit:
                logger.warning(f"Unit mismatch for PM Settings {pm_settings.id}: PM settings use {pm_settings.interval_unit}, meter reading uses {meter_reading_unit}")
                continue
            
            # Calculate next triggers
            triggers = PMAutomationService._calculate_next_triggers(pm_settings, meter_reading_value)
            logger.info(f"Calculated {len(triggers)} triggers for PM Settings {pm_settings.id}: {triggers}")
            
            # Check for early-create windows
            created_work_orders = []
            for trigger_value in triggers:
                work_order = PMAutomationService._check_and_create_work_order(
                    pm_settings, trigger_value, meter_reading_value, user
                )
                if work_order:
                    created_work_orders.append(work_order)
                    logger.info(f"Created PM work order {work_order.id} for PM Settings {pm_settings.id} at trigger {trigger_value}")
            
            all_created_work_orders.extend(created_work_orders)
        
        return all_created_work_orders
    
    @staticmethod
    def _get_active_pm_settings(asset_id):
        """Get active PM settings for an asset"""
        try:
            # Handle asset_id in format "app_label.model.uuid"
            if isinstance(asset_id, str) and '.' in asset_id:
                parts = asset_id.split('.')
                if len(parts) >= 3:
                    app_label = parts[0]
                    model_name = parts[1]
                    object_id = '.'.join(parts[2:])  # Handle UUIDs with hyphens
                    
                    # Get content type
                    content_type = ContentType.objects.get(app_label=app_label, model=model_name)
                    logger.debug(f"Looking for active PM settings with content_type={content_type}, object_id={object_id}")
                    
                    pm_settings = PMSettings.objects.filter(
                        content_type=content_type,
                        object_id=object_id,
                        is_active=True
                    )
                    
                    if pm_settings.exists():
                        logger.debug(f"Found {pm_settings.count()} active PM settings")
                    else:
                        logger.debug(f"No active PM settings found for content_type={content_type}, object_id={object_id}")
                    
                    return pm_settings
            
            # Fallback to original method
            content_type, object_id = get_content_type_and_asset_id(asset_id)
            logger.debug(f"Looking for active PM settings with content_type={content_type}, object_id={object_id}")
            
            pm_settings = PMSettings.objects.filter(
                content_type=content_type,
                object_id=object_id,
                is_active=True
            )
            
            if pm_settings.exists():
                logger.debug(f"Found {pm_settings.count()} active PM settings")
            else:
                logger.debug(f"No active PM settings found for content_type={content_type}, object_id={object_id}")
            
            return pm_settings
        except Exception as e:
            logger.error(f"Error getting PM settings for asset {asset_id}: {e}")
            return PMSettings.objects.none()
    
    @staticmethod
    def _calculate_next_triggers(pm_settings, current_meter_reading):
        """Calculate the next trigger values for floating trigger system"""
        triggers = []
        next_trigger = pm_settings.get_next_trigger()
        
        logger.debug(f"Calculating triggers: current_reading={current_meter_reading}, next_trigger={next_trigger}, interval={pm_settings.interval_value}, lead_time={pm_settings.lead_time_value}")
        
        # Calculate the early-create window
        early_create_window = next_trigger - pm_settings.lead_time_value
        
        logger.debug(f"Early create window: {early_create_window} (next_trigger {next_trigger} - lead_time {pm_settings.lead_time_value})")
        
        # For floating trigger system, we only create one trigger at a time
        # Check if we're in the early-create window
        if current_meter_reading >= early_create_window:
            # Only add trigger if it hasn't been handled yet
            if pm_settings.last_handled_trigger is None or next_trigger > pm_settings.last_handled_trigger:
                triggers.append(next_trigger)
                logger.debug(f"Added floating trigger: {next_trigger} (current reading {current_meter_reading} >= early window {early_create_window})")
        
        return triggers
    
    @staticmethod
    def _check_and_create_work_order(pm_settings, trigger_value, current_meter_reading, user):
        """
        Check if a work order should be created for this trigger
        """
        logger.debug(f"Checking work order creation for trigger {trigger_value}, current reading {current_meter_reading}")
        
        # Calculate early-create window
        early_create_window = trigger_value - pm_settings.lead_time_value
        
        logger.debug(f"Early create window: {early_create_window} (trigger {trigger_value} - lead time {pm_settings.lead_time_value})")
        
        # Check if we're in the early-create window
        if current_meter_reading < early_create_window:
            logger.debug(f"Current reading {current_meter_reading} < early create window {early_create_window}, skipping")
            return None
        
        logger.info(f"Current reading {current_meter_reading} >= early create window {early_create_window}, proceeding with work order creation")
        
        # Check if there's already an open PM work order for this trigger
        existing_trigger = PMTrigger.objects.filter(
            pm_settings=pm_settings,
            trigger_value=trigger_value,
            is_handled=False
        ).first()
        
        if existing_trigger and existing_trigger.work_order:
            logger.debug(f"Existing trigger found with work order {existing_trigger.work_order.id}, skipping")
            return None
        
        # Create the work order
        work_order = PMAutomationService._create_pm_work_order(
            pm_settings, trigger_value, user
        )
        
        # Check if work order creation failed
        if not work_order:
            logger.error(f"Failed to create work order for trigger {trigger_value}")
            return None
        
        # Create or update the trigger record using get_or_create to handle unique constraint
        pm_trigger, created = PMTrigger.objects.get_or_create(
            pm_settings=pm_settings,
            trigger_value=trigger_value,
            defaults={
                'trigger_unit': pm_settings.interval_unit,
                'work_order': work_order,
                'is_handled': False
            }
        )
        
        if created:
            logger.debug(f"Created new trigger {pm_trigger.id} for work order {work_order.id}")
        else:
            # Update existing trigger with the new work order
            pm_trigger.work_order = work_order
            pm_trigger.is_handled = False  # Reset to unhandled
            pm_trigger.save()
            logger.debug(f"Updated existing trigger {pm_trigger.id} with work order {work_order.id}")
        
        return work_order
    
    @staticmethod
    def _create_pm_work_order(pm_settings, trigger_value, user):
        """Create a PM work order and log the creation with the system admin as user"""
        logger.info(f"Creating PM work order for trigger {trigger_value}")
        
        # Increment the trigger counter
        new_counter = pm_settings.increment_trigger_counter()
        logger.info(f"Incremented trigger counter to {new_counter}")
        
        # Get iterations that should be triggered based on counter logic
        triggered_iterations = pm_settings.get_iterations_for_trigger()
        if not triggered_iterations:
            logger.error(f"No iterations found for PM Settings {pm_settings.id}")
            return None
        
        logger.info(f"Triggered iterations: {[f'{it.name} (order: {it.order})' for it in triggered_iterations]}")
        
        # Get the asset using the GenericForeignKey
        asset = None
        try:
            asset = pm_settings.asset
            logger.debug(f"Retrieved asset: {asset}, type: {type(asset)}")
        except Exception as e:
            logger.error(f"Error accessing asset from pm_settings: {e}")
            # Try to get the asset using content_type and object_id
            try:
                content_type = pm_settings.content_type
                model_class = content_type.model_class()
                asset = model_class.objects.get(pk=pm_settings.object_id)
                logger.debug(f"Retrieved asset using direct lookup: {asset}, type: {type(asset)}")
            except Exception as e2:
                logger.error(f"Error accessing asset using direct lookup: {e2}")
                return None
        
        # Ensure we have a valid asset object
        if not asset or hasattr(asset, 'all'):  # RelatedManager has 'all' method
            logger.error(f"Invalid asset object: {asset}, type: {type(asset)}")
            # Try one more time with direct lookup
            try:
                content_type = pm_settings.content_type
                model_class = content_type.model_class()
                asset = model_class.objects.get(pk=pm_settings.object_id)
                logger.debug(f"Retrieved asset using final direct lookup: {asset}, type: {type(asset)}")
            except Exception as e3:
                logger.error(f"Final attempt to get asset failed: {e3}")
                return None
        
        # Get the system admin user for the current tenant using connection.schema_name
        try:
            current_schema = connection.schema_name
            system_admin = TenantUser.objects.get(
                email=f'Sys_Admin@{current_schema}.tenmil.ca'
            )
            logger.debug(f"Found system admin: {system_admin}")
        except TenantUser.DoesNotExist:
            logger.warning(f"System admin not found for schema {current_schema}, using user {user}")
            system_admin = user
        
        # Get active status
        active_status = WorkOrderStatusNames.objects.filter(
            control__name='Active'
        ).first()
        
        if not active_status:
            from core.models import WorkOrderStatusControls
            active_control = WorkOrderStatusControls.objects.filter(key='active').first()
            if not active_control:
                active_control = WorkOrderStatusControls.objects.create(
                    key='active',
                    name='Active',
                    color='#4caf50',
                    order=1
                )
            active_status = WorkOrderStatusNames.objects.create(
                name='Active',
                control=active_control
            )
            logger.debug(f"Created active status: {active_status}")
        
        # Create work order description with consistent format
        iteration_names = [it.name for it in triggered_iterations]
        
        # Get the largest triggered iteration for the description
        if triggered_iterations:
            largest_iteration = max(triggered_iterations, key=lambda x: x.interval_value)
            iteration_value = int(largest_iteration.interval_value)
        else:
            # Fallback to PM interval if no iterations triggered
            iteration_value = int(pm_settings.interval_value)
        
        # Create description: pm name + iteration interval + unit (same format as manual)
        unit_formatted = pm_settings.interval_unit.title()  # Proper capitalization
        
        if pm_settings.name:
            # Use PM settings name if available
            description = f"{pm_settings.name} {iteration_value} {unit_formatted}"
        else:
            # Fallback to generic PM naming
            description = f"{iteration_value} {unit_formatted} PM"
        
        # Create work order (do NOT set created_by)
        trigger_meter_reading = MeterReading.objects.filter(
            object_id=asset.id
        ).order_by('-created_at').first().meter_reading
        work_order = WorkOrder.objects.create(
            content_type=pm_settings.content_type,
            object_id=pm_settings.object_id,
            status=active_status,
            maint_type='PM',
            priority='medium',
            description=description,
            is_pm_generated=True,
            trigger_meter_reading=trigger_meter_reading
        )
        
        logger.info(f"Created work order {work_order.id}: {work_order.description}")
        
        # Copy the cumulative checklist for all triggered iterations
        try:
            # Get the highest-order iteration (which will have the most comprehensive checklist)
            highest_order_iteration = max(triggered_iterations, key=lambda x: x.order)
            
            # Copy the cumulative checklist for the highest-order iteration
            pm_settings.copy_iteration_checklist_to_work_order(work_order, highest_order_iteration)
            logger.info(f"Copied cumulative checklist for highest-order iteration '{highest_order_iteration.name}' to work order {work_order.id}")
        except Exception as e:
            logger.error(f"Error copying iteration checklists to work order {work_order.id}: {e}")
        
        # Log creation with system admin as user
        WorkOrderLog.objects.create(
            work_order=work_order,
            amount=0,
            log_type=WorkOrderLog.LogTypeChoices.CREATED,
            user=system_admin,
            description="Work Order Created (PM Automation)"
        )
        
        logger.info(f"Created work order log for work order {work_order.id}")
        return work_order
    
    @staticmethod
    def handle_work_order_completion(work_order, closing_meter_reading):
        """
        Handle work order completion and update PM settings
        
        Args:
            work_order: The completed work order
            closing_meter_reading: The meter reading at completion
        """
        logger.info(f"Handling work order completion for {work_order.id} with closing reading {closing_meter_reading}")
        
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
        
        # Update PM settings with the closing meter reading
        pm_settings = pm_trigger.pm_settings
        pm_settings.update_next_trigger(closing_meter_reading)
        
        logger.info(f"Updated PM settings next trigger to {pm_settings.next_trigger_value}")
    
    @staticmethod
    def get_asset_pm_status(asset_id):
        """
        Get PM status for an asset including next triggers and active settings
        """
        pm_settings_list = PMAutomationService._get_active_pm_settings(asset_id)
        if not pm_settings_list.exists():
            return None
        
        # Get open PM work orders for all PM settings
        open_work_orders = WorkOrder.objects.none()
        pending_triggers = PMTrigger.objects.none()
        
        for pm_settings in pm_settings_list:
            # Get open PM work orders for this PM setting
            pm_work_orders = WorkOrder.objects.filter(
                content_type=pm_settings.content_type,
                object_id=pm_settings.object_id,
                maint_type='PM',
                is_closed=False
            )
            open_work_orders = open_work_orders.union(pm_work_orders)
            
            # Get pending triggers for this PM setting
            pm_triggers = PMTrigger.objects.filter(
                pm_settings=pm_settings,
                is_handled=False
            )
            pending_triggers = pending_triggers.union(pm_triggers)
        
        return {
            'pm_settings': pm_settings_list,
            'pm_settings_count': pm_settings_list.count(),
            'open_work_orders': open_work_orders,
            'pending_triggers': pending_triggers,
            'has_active_settings': pm_settings_list.filter(is_active=True).exists()
        }
