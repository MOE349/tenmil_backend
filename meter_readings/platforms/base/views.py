from configurations.base_features.views.base_api_view import BaseAPIView
from meter_readings.helpers import get_old_meter_reading
from meter_readings.models import *
from meter_readings.platforms.base.serializers import *
from configurations.base_features.exceptions.base_exceptions import LocalBaseException

class MeterReadingBaseView(BaseAPIView):
    serializer_class = MeterReadingBaseSerializer
    model_class = MeterReading

    def validate_data(self, data):
        asset_id = data.get('object_id')
        reading = float(data.get('meter_reading'))
        old_meter_reading = get_old_meter_reading(asset_id)
        
        if old_meter_reading >= reading:
            raise LocalBaseException(exception='old meter reading cannot be greater than new meter reading', status_code=400)
        data['old_meter_reading'] = old_meter_reading
        return data
    
    def handle_post_data(self, request):
        data = super().handle_post_data(request)
        data['created_by'] = request.user.id
        return data
    
    def create(self, data, params, return_instance=False, *args, **kwargs):
        print(data)
        asset_id = data.get('asset')
        reading = float(data.get('meter_reading'))
        data = self.validate_data(data)
        meter_reading, error, code = self.model_class.objects.get_object_or_404(asset=asset_id, meter_reading=reading, raise_exception=False)
        if meter_reading:
            if return_instance:
                return meter_reading
            else:
                raise LocalBaseException(exception='Meter reading already exists', status_code=400)
        
        return super().create(data, params, return_instance, *args, **kwargs)

    