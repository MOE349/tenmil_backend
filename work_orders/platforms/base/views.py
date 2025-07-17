from configurations.base_features.exceptions.base_exceptions import LocalBaseException
from configurations.base_features.views.base_api_view import BaseAPIView
from work_orders.models import *
from work_orders.platforms.base.serializers import *


class WorkOrderBaseView(BaseAPIView):
    serializer_class = WorkOrderBaseSerializer
    model_class = WorkOrder


    def handle_post_data(self, request):        
        data =  super().handle_post_data(request)
        # data = self.validate_post_data(data)
        return data
    
    # def validate_post_data(self, data):
    #     opened_work_orders = WorkOrder.objects.filter(status__control__name='Active', object_id=data.get('object_id'))
    #     if opened_work_orders.exists():
    #         raise LocalBaseException(exception="There is an opened work order, please close it first")
    #     return data
    
    def create(self, data, params, return_instance=False, *args, **kwargs):
        if "status" not in data:
            data['status'] = WorkOrderStatusNames.objects.get(name="Active").pk
        # Code will be auto-generated in the model's save method
        instance, response = super().create(data, params, return_instance=True, *args, **kwargs)
        WorkOrderLog.objects.create(work_order=instance, amount=0, log_type=WorkOrderLog.LogTypeChoices.CREATED, user=params['user'], description="Work Order Created")
        return self.format_response(data=response, status_code=201)
    
    def handle_update_data(self, request):
        data = super().handle_update_data(request)
        return data

    def update(self, data, params,  pk, partial,  *args, **kwargs):
        amount = data.pop('amount', 0)
        status = data.get('status', None)
        if status:
            status_instance = WorkOrderStatusNames.objects.get_object_or_404(id=status, raise_exception=True)
        else:
            status_instance = WorkOrderStatusNames.objects.get_object_or_404(name="Active", raise_exception=True)
        status = status_instance.control.name if status_instance else "Active"
        
        """Update an object"""
        user_lang = params.pop('lang', 'en')
        instance = self.get_instance(pk)

        if status == "Closed":
            # Check if completion meter reading is provided
            if ('completion_meter_reading' not in data or data.get('completion_meter_reading') is None) and not instance.completion_meter_reading:
                # We'll handle this after getting the instance
                needs_meter_reading = True
            else:
                needs_meter_reading = False
            
        elif status != 'Closed' and instance.status.control.name == "Closed":
            instance.is_reopened = True
            instance.save()
            WorkOrderLog.objects.create(work_order=instance, amount=amount, log_type=WorkOrderLog.LogTypeChoices.REOPENED, user=params['user'], description="Work Order Reopened")
        
        # Handle completion meter reading for closed status
        if status == "Closed" and needs_meter_reading:
            from meter_readings.models import MeterReading
            latest_meter_reading = MeterReading.objects.filter(
                content_type=instance.content_type,
                object_id=instance.object_id
            ).order_by('-created_at').first()
            
            if latest_meter_reading:
                data['completion_meter_reading'] = latest_meter_reading.meter_reading
                print(f"Auto-filled completion meter reading: {latest_meter_reading.meter_reading}")
            else:
                raise LocalBaseException(exception="No meter readings found for this asset")
        
        is_closed = instance.is_closed
        serializer = self.serializer_class(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response = serializer.data
        if status == "Closed":
            instance.is_closed = True
            instance.status = status_instance
            instance.save()
            WorkOrderLog.objects.create(work_order=instance, amount=amount, log_type=WorkOrderLog.LogTypeChoices.COMPLETED, user=params['user'], description="Work Order Closed")
        else:
            instance.is_closed = False
            instance.status = status_instance
            instance.save()               
            WorkOrderLog.objects.create(work_order=instance, amount=amount, log_type=WorkOrderLog.LogTypeChoices.UPDATED, user=params['user'], description="Work Order Updated")
        response['status'] = WorkOrderStatusNamesBaseSerializer(instance.status).data
        return self.format_response(data=response, status_code=200)
    

class WorkOrderChecklistBaseView(BaseAPIView):
    serializer_class = WorkOrderChecklistBaseSerializer
    model_class = WorkOrderChecklist




class WorkOrderLogBaseView(BaseAPIView):
    serializer_class = WorkOrderLogBaseSerializer
    model_class = WorkOrderLog
    http_method_names=['get']

    def get_request_params(self, request):
        params = super().get_request_params(request)
        params['ordering'] = "created_at"
        return params



class WorkOrderMiscCostBaseView(BaseAPIView):
    serializer_class = WorkOrderMiscCostBaseSerializer
    model_class = WorkOrderMiscCost


class WorkOrderStatusNamesBaseView(BaseAPIView):
    serializer_class = WorkOrderStatusNamesBaseSerializer
    model_class = WorkOrderStatusNames


class WorkOrderStatusControlsBaseView(BaseAPIView):
    serializer_class = WorkOrderStatusControlsBaseSerializer
    model_class = WorkOrderStatusControls

    def destroy(self, request, pk, *args, **kwargs):
        params = self.get_request_params(request)
        user_lang = params.pop('lang', 'en')
        instance = self.get_instance(pk)
        if instance.is_system_level:
            raise LocalBaseException(exception="System level status cannot be deleted")
        instance.delete()
        return self.format_response(data={}, status_code=204)
    

class WorkOrderCompletionNoteBaseView(BaseAPIView):
    serializer_class = WorkOrderCompletionNoteBaseSerializer
    model_class = WorkOrderCompletionNote

    def get(self, request, pk=None, params=None, allow_unauthenticated_user=False, *args, **kwargs):
        if params is None:
            params = self.get_request_params(request)
        params = self.clear_paginations_params(params)
        instance, errors, status_code= self.model_class.objects.get_object_or_404(raise_exception=False, **params)
        pk = instance.pk if instance else None
        return super().get(request, pk, params, allow_unauthenticated_user, *args, **kwargs)

    def handle_post_data(self, request):
        data = super().handle_post_data(request)
        data['user'] = self.get_request_user(request).pk
        return data


    def post(self, request, allow_unauthenticated_user=False, *args, **kwargs):
        try:
            instance, error, _ = self.model_class.objects.get_object_or_404(raise_exception=False, work_order=request.data.get("work_order"))
            return super().patch(request, instance.pk, *args, **kwargs)
        except:
            return super().post(request, allow_unauthenticated_user, *args, **kwargs)
       