from assets.services import get_assets_by_gfk
from meter_readings.models import MeterReading


def get_old_meter_reading(asset_id, previous_instance=None):
    print("get_old_meter_reading", asset_id)
    if not previous_instance:
        previous_instance = get_previous_meter_reading(asset_id)
    if previous_instance:
        old_meter_reading = previous_instance.meter_reading
    else:
        old_meter_reading = 0
    return old_meter_reading

def get_previous_meter_reading(asset_id):
    return get_assets_by_gfk(model_class=MeterReading, id=asset_id).order_by("-created_at").first()
