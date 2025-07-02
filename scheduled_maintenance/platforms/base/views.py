from configurations.base_features.exceptions.base_exceptions import LocalBaseException
from configurations.base_features.views.base_api_view import BaseAPIView
from scheduled_maintenance.helpers import generate_next_wo
from scheduled_maintenance.models import *
from scheduled_maintenance.platforms.base.serializers import *


class ScheduledMaintenanceBaseView(BaseAPIView):
    serializer_class = ScheduledMaintenanceBaseSerializer
    model_class = ScheduledMaintenance

    def create(self, data, params, return_instance=False, *args, **kwargs):
        if "trigger_type" in kwargs:
            trigger_type = kwargs["trigger_type"] # meter_reading_triggers || time_triggers
            print("data", data)
            if trigger_type == "meter_reading_triggers":
                every = data.pop("every", None)
                starting_at = data.pop("starting_at", None)
                circle_type = data.pop("circle_type", None)
                if not every or not starting_at or not circle_type:
                    raise LocalBaseException(exception="every, starting_at, circle_type are required", status_code=400)
                data['trigger_type'] = TriggerTypeChoices.METER_READING
                data['trigger_at'] = {"meter_reading": every}
                data['starting_at'] = starting_at
        instance, response =  super().create(data, params, return_instance=True, *args, **kwargs)
        if "meter_reading" in instance.trigger_at.keys():
            SmIttirationCycle.objects.create(scheduled_maintenance=instance, ittiration=instance.trigger_at["meter_reading"])
        return self.format_response(data=response, status_code=201)


class SmIttirationCycleBaseView(BaseAPIView):
    serializer_class = SmIttirationCycleBaseSerializer
    model_class = SmIttirationCycle


class SmLogBaseView(BaseAPIView):
    serializer_class = SmLogBaseSerializer
    model_class = SmLog
    

class SmIttirationCycleChecklistBaseView(BaseAPIView):
    serializer_class = SmIttirationCycleChecklistBaseSerializer
    model_class = SmIttirationCycleChecklist


class SMInfoBaseView(BaseAPIView):
    serializer_class = SMInfoBaseSerializer
    model_class = ScheduledMaintenance
    http_method_names = ['get', 'post']

    def get_request_params(self, request):
        params = request.query_params.copy()
        return params

   
    
    def handle_post_data(self, request):
        data = super().handle_post_data(request)
        data['user'] = self.get_request_user(request)
        return data

    def post(self, request, allow_unauthenticated_user=False, *args, **kwargs):
        try:
            data = self.handle_post_data(request)
            params = self.get_request_params(request)
            params = self.handle_post_params(request, params, allow_unauthenticated_user)
            generate_next_wo(data, params)
            return self.format_response({"message": "success"}, [], 200)
        except Exception as e:
            return self.handle_exception(e)