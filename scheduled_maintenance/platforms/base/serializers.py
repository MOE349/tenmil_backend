from configurations.base_features.serializers.base_serializer import BaseSerializer
from meter_readings.models import MeterReading
from scheduled_maintenance.helpers import calculate_next_trigger
from scheduled_maintenance.models import *

class ScheduledMaintenanceBaseSerializer(BaseSerializer):
    class Meta:
        model = ScheduledMaintenance
        fields = '__all__'


class SmIttirationCycleBaseSerializer(BaseSerializer):
    class Meta:
        model = SmIttirationCycle
        fields = '__all__'


class SmLogBaseSerializer(BaseSerializer):
    class Meta:
        model = SmLog
        fields = '__all__'
        

        
class SmIttirationCycleChecklistBaseSerializer(BaseSerializer):
    class Meta:
        model = SmIttirationCycleChecklist
        fields = '__all__'

class SMInfoBaseSerializer(BaseSerializer):
    class Meta:
        model = ScheduledMaintenance
        fields = '__all__'

    def to_representation(self, instance):
        next_trigger, next_cycle, ittirations = calculate_next_trigger(instance.asset.id)
        meter_reading = int(MeterReading.objects.filter(asset=instance.asset.id).order_by('-meter_reading').first().meter_reading) if MeterReading.objects.filter(asset=instance.asset.id) else None
        res = super().to_representation(instance)
        # res['current_meter_reading'] = meter_reading.order_by('-meter_reading').first().meter_reading if meter_reading else None
        res['next_trigger'] =  next_trigger
        res['next_cycle'] =  next_cycle
        res['last_meter_reading'] =  meter_reading
        res['ittirations'] = ittirations
        res['ittiration_cycles'] = SmIttirationCycleBaseSerializer(SmIttirationCycle.objects.filter(scheduled_maintenance=instance), many=True).data
        return res
