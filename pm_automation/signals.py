from django.db.models.signals import post_save
from django.dispatch import receiver
from meter_readings.models import MeterReading
from work_orders.models import WorkOrder
from pm_automation.services import PMAutomationService


@receiver(post_save, sender=MeterReading)
def handle_meter_reading_save(sender, instance, created, **kwargs):
    """
    Handle new meter reading saves and trigger PM automation
    """
    if created:
        # Get the asset ID from the meter reading
        asset_id = f"{instance.content_type.app_label}.{instance.content_type.model}.{instance.object_id}"
        
        # Process PM automation
        created_work_orders = PMAutomationService.process_meter_reading(
            asset_id=asset_id,
            meter_reading_value=instance.meter_reading,
            meter_reading_unit='hours',  # Default to hours, could be made configurable
            user=instance.created_by
        )
        
        if created_work_orders:
            print(f"Created {len(created_work_orders)} PM work orders for asset {asset_id}")


@receiver(post_save, sender=WorkOrder)
def handle_work_order_completion(sender, instance, **kwargs):
    """
    Handle work order completion and update PM settings
    """
    # Check if this is a PM work order that was just completed
    if instance.maint_type == 'PM' and instance.is_closed:
        # Get the completion meter reading if available
        completion_meter_reading = instance.completion_meter_reading
        
        if completion_meter_reading:
            PMAutomationService.handle_work_order_completion(
                work_order=instance,
                closing_meter_reading=completion_meter_reading
            ) 