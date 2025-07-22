from django.db.models.signals import post_save
from django.dispatch import receiver
from meter_readings.models import MeterReading
from pm_automation.models import PMSettings
from work_orders.models import WorkOrder
from pm_automation.services import PMAutomationService
import logging

# Set up logging
logger = logging.getLogger(__name__)

@receiver(post_save, sender=PMSettings)
def handle_pm_settings_save(sender, instance, created, **kwargs):
    """
    Handle PM settings saves and trigger PM automation
    """
    current_meter_reading = MeterReading.objects.filter(
        content_type=instance.content_type,
        object_id=instance.object_id
    ).order_by('-created_at').first()
    
    if current_meter_reading <= instance.next_trigger_value:
        PMAutomationService.process_meter_reading(
            asset_id=instance.object_id,
            meter_reading_value=current_meter_reading.meter_reading,
            meter_reading_unit=current_meter_reading.unit,
            user=current_meter_reading.created_by
        )


@receiver(post_save, sender=MeterReading)
def handle_meter_reading_save(sender, instance, created, **kwargs):
    """
    Handle new meter reading saves and trigger PM automation
    """
    if created:
        try:
            asset_str = str(instance.asset) if instance.asset else f"{instance.content_type.app_label}.{instance.content_type.model}.{instance.object_id}"
            logger.info(f"New meter reading created: {instance.id} - {instance.meter_reading} for asset {asset_str}")
        except Exception:
            asset_str = f"{instance.content_type.app_label}.{instance.content_type.model}.{instance.object_id}"
            logger.info(f"New meter reading created: {instance.id} - {instance.meter_reading} for asset {asset_str}")
        
        # Get the asset ID from the meter reading
        asset_id = f"{instance.content_type.app_label}.{instance.content_type.model}.{instance.object_id}"
        logger.info(f"Processing PM automation for asset_id: {asset_id}")
        
        # Process PM automation
        try:
            created_work_orders = PMAutomationService.process_meter_reading(
                asset_id=asset_id,
                meter_reading_value=instance.meter_reading,
                meter_reading_unit='hours',  # Default to hours, could be made configurable
                user=instance.created_by
            )
            
            if created_work_orders:
                logger.info(f"Created {len(created_work_orders)} PM work orders for asset {asset_id}")
                for wo in created_work_orders:
                    logger.info(f"  - Created work order {wo.id}: {wo.description}")
            else:
                logger.info(f"No PM work orders created for asset {asset_id}")
                
        except Exception as e:
            logger.error(f"Error processing PM automation for asset {asset_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())


@receiver(post_save, sender=WorkOrder)
def handle_work_order_completion(sender, instance, **kwargs):
    """
    Handle work order completion and update PM settings
    """
    # Check if this is a PM work order that was just completed
    if instance.maint_type == 'PM' and instance.is_closed and not instance.is_reopened:
        logger.info(f"PM work order {instance.id} completed")
        
        # Get the completion meter reading if available
        completion_meter_reading = instance.completion_meter_reading
        
        if completion_meter_reading:
            logger.info(f"Handling completion with meter reading: {completion_meter_reading}")
            try:
                PMAutomationService.handle_work_order_completion(
                    work_order=instance,
                    closing_meter_reading=completion_meter_reading
                )
                logger.info(f"Successfully handled work order completion for {instance.id}")
            except Exception as e:
                logger.error(f"Error handling work order completion for {instance.id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.warning(f"PM work order {instance.id} completed but no completion meter reading provided")
