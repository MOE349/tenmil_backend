from configurations.base_features.exceptions.base_exceptions import LocalBaseException
from meter_readings.models import MeterReading
from scheduled_maintenance.models import ScheduledMaintenance, SmIttirationCycle
from work_orders.models import WorkOrder
from work_orders.platforms.base.views import WorkOrderBaseView


def calculate_next_trigger(asset_id):
    next_trigger, next_cycle, ittirations = 0, 0, []
    work_orders = WorkOrder.objects.filter(asset__id=asset_id, status__control__name='Closed', user__name="System Admin")
    ittiration_cycle = 0
    if work_orders:
        last_work_order = work_orders.order_by('-created_at').first()
        last_wo_mr = last_work_order.completion_meter_reading
        fixed_last_wo_mr = last_work_order.completion_meter_reading
        ittiration_cycle = last_work_order.ittiration_cycle
    
    ittiration_cycles = SmIttirationCycle.objects.filter(scheduled_maintenance__asset__id=asset_id)
    ittirations = sorted([ittiration_cycle.ittiration for ittiration_cycle in ittiration_cycles])
    next_cycle = ittirations[ittiration_cycles.filter(ittiration__gt=ittiration_cycle).count()]
        




    # meter_readings = MeterReading.objects.filter(asset__id=asset_id)
    # meter_reading = None
    # if meter_readings:
    #     meter_reading = meter_readings.order_by('-created_at').first().meter_reading
    # sm = ScheduledMaintenance.objects.filter(asset__id=asset_id)
    # ittiration_cycles = SmIttirationCycle.objects.filter(scheduled_maintenance__asset__id=asset_id)
    # ittirations = sorted([ittiration_cycle.ittiration for ittiration_cycle in ittiration_cycles])
    # next_trigger = 0
    # next_cycle = 500

    # # get last work order meter reading
    # last_wo_mr = 0
    # fixed_last_wo_mr = 0
    # work_orders = WorkOrder.objects.filter(asset__id=asset_id, status__control__name='Closed')
    # if work_orders:
    #     last_work_order = work_orders.order_by('-created_at').first()
    #     last_wo_mr = last_work_order.completion_meter_reading
    #     fixed_last_wo_mr = last_work_order.completion_meter_reading
    # # minimize last work order to fit within itterations rate
    # while fixed_last_wo_mr > max(ittirations):
    #     fixed_last_wo_mr -= max(ittirations)
    # future_ittirations = [itt for itt in ittirations if itt >= fixed_last_wo_mr]
    # past_ittirations = [itt for itt in ittirations if itt < fixed_last_wo_mr]
    # next_cycle = min(future_ittirations)
    # next_trigger = max(past_ittirations) + last_wo_mr
    # return next_trigger, next_cycle, ittirations

def generate_next_wo(data, params):
    asset_id = data.get('asset_id', None)
    next_work_order = data.get('next_work_order', None)
    if not asset_id or not next_work_order:
        raise LocalBaseException(exception='asset_id and next_work_order are required')
    data['maint_type']="hd"
    data['asset']=asset_id
    data['priority']='high'
    data['description'] = "Next scheduled maintenance"
    wo_view = WorkOrderBaseView()
    data = wo_view.validate_post_data(data)
    response = wo_view.create(data, params)
    return response
    