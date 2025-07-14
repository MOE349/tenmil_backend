from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from pm_automation.models import PMSettings, PMTrigger, PMUnitChoices
from work_orders.models import WorkOrder, WorkOrderStatusNames
from tenant_users.models import TenantUser
from assets.services import get_content_type_and_asset_id
from work_orders.models import WorkOrderLog
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
        
        # Get PM settings for this asset
        pm_settings = PMAutomationService._get_pm_settings(asset_id)
        if not pm_settings:
            logger.info(f"No PM settings found for asset {asset_id}")
            return None
        
        if not pm_settings.is_active:
            logger.info(f"PM settings inactive for asset {asset_id}")
            return None
        
        logger.info(f"Found active PM settings for asset {asset_id}: interval={pm_settings.interval_value} {pm_settings.interval_unit}, start_threshold={pm_settings.start_threshold_value} {pm_settings.start_threshold_unit}, lead_time={pm_settings.lead_time_value} {pm_settings.lead_time_unit}")
        
        # Check if units match
        if pm_settings.interval_unit != meter_reading_unit:
            logger.warning(f"Unit mismatch: PM settings use {pm_settings.interval_unit}, meter reading uses {meter_reading_unit}")
            return None
        
        # Calculate next triggers
        triggers = PMAutomationService._calculate_next_triggers(pm_settings, meter_reading_value)
        logger.info(f"Calculated {len(triggers)} triggers for asset {asset_id}: {triggers}")
        
        # Check for early-create windows
        created_work_orders = []
        for trigger_value in triggers:
            work_order = PMAutomationService._check_and_create_work_order(
                pm_settings, trigger_value, meter_reading_value, user
            )
            if work_order:
                created_work_orders.append(work_order)
                logger.info(f"Created PM work order {work_order.id} for asset {asset_id} at trigger {trigger_value}")
        
        return created_work_orders
    
    @staticmethod
    def _get_pm_settings(asset_id):
        """Get PM settings for an asset"""
        try:
            content_type, object_id = get_content_type_and_asset_id(asset_id)
            logger.debug(f"Looking for PM settings with content_type={content_type}, object_id={object_id}")
            
            pm_settings = PMSettings.objects.filter(
                content_type=content_type,
                object_id=object_id,
                is_active=True
            ).first()
            
            if pm_settings:
                logger.debug(f"Found PM settings: {pm_settings}")
            else:
                logger.debug(f"No PM settings found for content_type={content_type}, object_id={object_id}")
            
            return pm_settings
        except Exception as e:
            logger.error(f"Error getting PM settings for asset {asset_id}: {e}")
            return None
    
    @staticmethod
    def _calculate_next_triggers(pm_settings, current_meter_reading):
        """Calculate the next trigger values"""
        triggers = []
        next_trigger = pm_settings.get_next_trigger()
        
        logger.debug(f"Calculating triggers: current_reading={current_meter_reading}, next_trigger={next_trigger}, interval={pm_settings.interval_value}")
        
        # Keep adding interval until we exceed the current meter reading
        while next_trigger <= current_meter_reading:
            if next_trigger > pm_settings.last_handled_trigger or pm_settings.last_handled_trigger is None:
                triggers.append(next_trigger)
                logger.debug(f"Added trigger: {next_trigger}")
            next_trigger += pm_settings.interval_value
        
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
        
        # Create or update the trigger record
        if existing_trigger:
            existing_trigger.work_order = work_order
            existing_trigger.save()
            logger.debug(f"Updated existing trigger {existing_trigger.id} with work order {work_order.id}")
        else:
            new_trigger = PMTrigger.objects.create(
                pm_settings=pm_settings,
                trigger_value=trigger_value,
                trigger_unit=pm_settings.interval_unit,
                work_order=work_order,
                is_handled=False
            )
            logger.debug(f"Created new trigger {new_trigger.id} for work order {work_order.id}")
        
        return work_order
    
    @staticmethod
    def _create_pm_work_order(pm_settings, trigger_value, user):
        """Create a PM work order and log the creation with the system admin as user"""
        logger.info(f"Creating PM work order for trigger {trigger_value}")
        
        # Get the asset using the GenericForeignKey
        try:
            asset = pm_settings.asset
            logger.debug(f"Retrieved asset: {asset}")
        except Exception as e:
            logger.error(f"Error accessing asset from pm_settings: {e}")
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
        
        # Create work order (do NOT set created_by)
        work_order = WorkOrder.objects.create(
            content_type=pm_settings.content_type,
            object_id=pm_settings.object_id,
            status=active_status,
            maint_type='PM',
            priority='medium',
            description=f"Meter-driven PM for {asset.code} at {trigger_value} {pm_settings.interval_unit}"
        )
        
        logger.info(f"Created work order {work_order.id}: {work_order.description}")
        
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
        pm_settings = PMAutomationService._get_pm_settings(asset_id)
        if not pm_settings:
            return None
        
        # Get open PM work orders
        open_work_orders = WorkOrder.objects.filter(
            content_type=pm_settings.content_type,
            object_id=pm_settings.object_id,
            maint_type='PM',
            is_closed=False
        )
        
        # Get pending triggers
        pending_triggers = PMTrigger.objects.filter(
            pm_settings=pm_settings,
            is_handled=False
        )
        
        return {
            'pm_settings': pm_settings,
            'next_trigger': pm_settings.get_next_trigger(),
            'open_work_orders': open_work_orders,
            'pending_triggers': pending_triggers,
            'is_active': pm_settings.is_active
        } 