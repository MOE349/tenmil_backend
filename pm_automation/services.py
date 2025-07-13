from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from pm_automation.models import PMSettings, PMTrigger, PMUnitChoices
from work_orders.models import WorkOrder, WorkOrderStatusNames
from tenant_users.models import TenantUser
from assets.services import get_content_type_and_asset_id
from work_orders.models import WorkOrderLog


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
        # Get PM settings for this asset
        pm_settings = PMAutomationService._get_pm_settings(asset_id)
        if not pm_settings or not pm_settings.is_active:
            return None
        
        # Check if units match
        if pm_settings.interval_unit != meter_reading_unit:
            return None
        
        # Calculate next triggers
        triggers = PMAutomationService._calculate_next_triggers(pm_settings, meter_reading_value)
        
        # Check for early-create windows
        created_work_orders = []
        for trigger_value in triggers:
            work_order = PMAutomationService._check_and_create_work_order(
                pm_settings, trigger_value, meter_reading_value, user
            )
            if work_order:
                created_work_orders.append(work_order)
        
        return created_work_orders
    
    @staticmethod
    def _get_pm_settings(asset_id):
        """Get PM settings for an asset"""
        try:
            content_type, object_id = get_content_type_and_asset_id(asset_id)
            return PMSettings.objects.filter(
                content_type=content_type,
                object_id=object_id,
                is_active=True
            ).first()
        except:
            return None
    
    @staticmethod
    def _calculate_next_triggers(pm_settings, current_meter_reading):
        """Calculate the next trigger values"""
        triggers = []
        next_trigger = pm_settings.get_next_trigger()
        
        # Keep adding interval until we exceed the current meter reading
        while next_trigger <= current_meter_reading:
            if next_trigger > pm_settings.last_handled_trigger or pm_settings.last_handled_trigger is None:
                triggers.append(next_trigger)
            next_trigger += pm_settings.interval_value
        
        return triggers
    
    @staticmethod
    def _check_and_create_work_order(pm_settings, trigger_value, current_meter_reading, user):
        """
        Check if a work order should be created for this trigger
        """
        # Calculate early-create window
        early_create_window = trigger_value - pm_settings.lead_time_value
        
        # Check if we're in the early-create window
        if current_meter_reading < early_create_window:
            return None
        
        # Check if there's already an open PM work order for this trigger
        existing_trigger = PMTrigger.objects.filter(
            pm_settings=pm_settings,
            trigger_value=trigger_value,
            is_handled=False
        ).first()
        
        if existing_trigger and existing_trigger.work_order:
            return None
        
        # Create the work order
        work_order = PMAutomationService._create_pm_work_order(
            pm_settings, trigger_value, user
        )
        
        # Create or update the trigger record
        if existing_trigger:
            existing_trigger.work_order = work_order
            existing_trigger.save()
        else:
            PMTrigger.objects.create(
                pm_settings=pm_settings,
                trigger_value=trigger_value,
                trigger_unit=pm_settings.interval_unit,
                work_order=work_order,
                is_handled=False
            )
        
        return work_order
    
    @staticmethod
    def _create_pm_work_order(pm_settings, trigger_value, user):
        """Create a PM work order and log the creation with the system admin as user"""
        asset = pm_settings.asset
        # Get the system admin user for the current tenant using connection.schema_name
        try:
            current_schema = connection.schema_name
            system_admin = TenantUser.objects.get(
                email=f'Sys_Admin@{current_schema}.tenmil.ca'
            )
        except TenantUser.DoesNotExist:
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
        # Create work order (do NOT set created_by)
        work_order = WorkOrder.objects.create(
            content_type=pm_settings.content_type,
            object_id=pm_settings.object_id,
            status=active_status,
            maint_type='PM',
            priority='medium',
            description=f"Meter-driven PM for {asset.name} at {trigger_value} {pm_settings.interval_unit}"
        )
        # Log creation with system admin as user
        WorkOrderLog.objects.create(
            work_order=work_order,
            amount=0,
            log_type=WorkOrderLog.LogTypeChoices.CREATED,
            user=system_admin,
            description="Work Order Created (PM Automation)"
        )
        return work_order
    
    @staticmethod
    def handle_work_order_completion(work_order, closing_meter_reading):
        """
        Handle work order completion and update PM settings
        
        Args:
            work_order: The completed work order
            closing_meter_reading: The meter reading at completion
        """
        # Find the PM trigger for this work order
        pm_trigger = PMTrigger.objects.filter(work_order=work_order).first()
        if not pm_trigger:
            return
        
        # Update the trigger as handled
        pm_trigger.is_handled = True
        pm_trigger.handled_at = timezone.now()
        pm_trigger.save()
        
        # Update PM settings with the closing meter reading
        pm_settings = pm_trigger.pm_settings
        pm_settings.update_next_trigger(closing_meter_reading)
    
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