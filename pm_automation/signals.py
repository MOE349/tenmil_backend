from django.db.models.signals import post_save
from django.dispatch import receiver
from meter_readings.models import MeterReading
from pm_automation.models import PMSettings, PMIteration
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
    # If this is a new PM Settings, create the first iteration automatically
    if created:
        try:
            # Create the first iteration with the base interval value
            first_iteration = PMIteration.objects.create(
                pm_settings=instance,
                interval_value=instance.interval_value,
                name=f"{instance.interval_value} {instance.interval_unit}"
            )
            logger.info(f"Created first iteration for PM Settings {instance.id}: {first_iteration.name}")
        except Exception as e:
            logger.error(f"Error creating first iteration for PM Settings {instance.id}: {e}")
    
    # Remove the PM automation trigger from here to prevent double processing
    # The automation should only be triggered by meter reading saves


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
    if instance.is_pm_generated and instance.is_closed and not instance.is_reopened:
        logger.info(f"PM work order {instance.id} completed")
        
        # Find the PM trigger to determine PM type
        from pm_automation.models import PMTrigger, PMTriggerTypes
        pm_trigger = PMTrigger.objects.filter(work_order=instance).first()
        
        if pm_trigger and pm_trigger.pm_settings:
            pm_settings = pm_trigger.pm_settings
            
            if pm_settings.trigger_type == PMTriggerTypes.CALENDAR:
                # Handle calendar PM completion
                logger.info(f"Handling calendar PM work order completion for {instance.id}")
                try:
                    from pm_automation.calendar_service import CalendarPMService
                    CalendarPMService.handle_calendar_work_order_completion(instance)
                    logger.info(f"Successfully handled calendar PM work order completion for {instance.id}")
                except Exception as e:
                    logger.error(f"Error handling calendar PM work order completion for {instance.id}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    
            elif pm_settings.trigger_type == PMTriggerTypes.METER_READING:
                # Handle meter PM completion (existing logic)
                completion_meter_reading = instance.completion_meter_reading
                
                if completion_meter_reading:
                    logger.info(f"Handling meter PM completion with meter reading: {completion_meter_reading}")
                    try:
                        PMAutomationService.handle_work_order_completion(
                            work_order=instance,
                            closing_meter_reading=completion_meter_reading
                        )
                        logger.info(f"Successfully handled meter PM work order completion for {instance.id}")
                    except Exception as e:
                        logger.error(f"Error handling meter PM work order completion for {instance.id}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                else:
                    logger.warning(f"Meter PM work order {instance.id} completed but no completion meter reading provided")
        else:
            logger.warning(f"PM work order {instance.id} completed but no PM trigger found")
