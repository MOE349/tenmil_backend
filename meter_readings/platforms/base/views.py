from assets.models import Attachment, Equipment
from configurations.base_features.views.base_api_view import BaseAPIView
from meter_readings.models import *
from meter_readings.platforms.base.serializers import *
from configurations.base_features.exceptions.base_exceptions import LocalBaseException

class MeterReadingBaseView(BaseAPIView):
    serializer_class = MeterReadingBaseSerializer
    model_class = MeterReading

    def validate_data(self, data):
        reading = float(data.get('meter_reading'))
        previous_instance = self.model_class.objects.filter(asset=data.get('asset')).order_by('-created_at').first()
        if previous_instance and previous_instance.meter_reading >= reading:
            raise LocalBaseException(exception='old meter reading cannot be greater than new meter reading', status_code=400)
        if previous_instance:
            data['old_meter_reading'] = previous_instance.meter_reading
        return data
    
    def handle_post_data(self, request):
        data = super().handle_post_data(request)
        data['created_by'] = request.user.id
        return data
    
    def create(self, data, params, return_instance=False, *args, **kwargs):
        asset = data.pop('asset')
        try:
            asset_instance, errors, status_code = Equipment.objects.get_object_or_404(id=asset, raise_exception=False)
        except:
            asset_instance = Attachment.objects.get_object_or_404(id=asset, raise_exception=True)
        asset = Asset.objects.get_object_or_404(id=asset_instance.asset_ptr.id, raise_exception=True)
        data['asset'] = asset.id
        data = self.validate_data(data)
        return super().create(data, params, return_instance, *args, **kwargs)

