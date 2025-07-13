from configurations.base_features.db.db_choices import TriggerTypeChoices
from meter_readings.helpers import get_old_meter_reading

from meter_readings.platforms.base.views import MeterReadingBaseView
from tenant_users.models import TenantUser
from work_orders.platforms.base.views import WorkOrderBaseView

# def create_meter_reading(sender, instance, created, **kwargs):
#     if created:
#          tenant = instance.created_by.tenant
#          asset_id = instance.object_id
#          meter_reading = instance.meter_reading
#          old_meter_reading = get_old_meter_reading(asset_id)
#          handle_sm_for_mr(tenant, asset_id, meter_reading, old_meter_reading)

# def updated_work_order(sender, instance, created, **kwargs):
#     view = MeterReadingBaseView()
#     user = TenantUser.objects.get(name="System Admin")
#     mr_data = {
#         "created_by": user.id,
#         "asset": instance.object_id
#     }
#     mr_params = {
        
#     }
#     if not created:
#         if instance.status.control.name == "Closed":
#             mr_data['meter_reading'] = instance.completion_meter_reading
#             view.create(data=mr_data, params=mr_params, return_instance=True)
#     else:
#             mr_data['meter_reading'] = instance.starting_meter_reading
#             view.create(data=mr_data, params=mr_params, return_instance=True)
    

# def handle_sm_for_mr(tenant, asset_id, meter_reading, old_meter_reading, *args, **kwargs):
#         sm = ScheduledMaintenance.objects.filter(object_id=asset_id, trigger_type=TriggerTypeChoices.METER_READING).first()
#         ittirations = SmIttirationCycle.objects.filter(scheduled_maintenance=sm)
#         for ittiration in ittirations:
#             if int(old_meter_reading) < ittiration.ittiration <= int(meter_reading):
                
#                 user = TenantUser.objects.get(tenant=tenant, email=f'Sys_Admin@{tenant.schema_name}.tenmil.ca')
#          