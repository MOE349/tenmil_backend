from configurations.base_features.serializers.base_serializer import BaseSerializer
from configurations.base_features.db.db_helpers import get_object_by_content_type_and_id
from assets.services import get_asset_serializer
from work_orders.platforms.base.serializers import WorkOrderBaseSerializer
from file_uploads.platforms.base.serializers import FileUploadSerializer
from components.models import *
from django.utils import timezone


class ComponentBaseSerializer(BaseSerializer):
    class Meta:
        model = Component
        fields = '__all__'
    
    def to_representation(self, instance):
        response = super().to_representation(instance)
        
        # Add asset information
        if instance.content_type and instance.object_id:
            asset = get_object_by_content_type_and_id(instance.content_type.id, instance.object_id)
            if asset:
                response['asset'] = get_asset_serializer(asset).data
        
        # Add work order information
        if instance.work_order:
            response['work_order'] = WorkOrderBaseSerializer(instance.work_order).data
        
        # Add files information
        files = instance.files.all()
        if files:
            response['files'] = FileUploadSerializer(files, many=True).data
        
        # Calculate and add component_meter_reading
        component_meter_reading = instance.get_component_meter_reading()
        response['component_meter_reading'] = component_meter_reading
        
        # Perform warranty validations and update instance if needed
        updated = False
        
        # Check meter reading warranty expiration
        if (instance.warranty_meter_reading is not None and 
            component_meter_reading > instance.warranty_meter_reading and 
            not instance.is_warranty_expired):
            instance.is_warranty_expired = True
            updated = True
            
        # Check date warranty expiration
        if (instance.warranty_exp_date is not None and 
            timezone.now().date() > instance.warranty_exp_date and 
            not instance.is_warranty_expired):
            instance.is_warranty_expired = True
            updated = True
        
        # Save the instance if warranty status changed
        if updated:
            instance.save(update_fields=['is_warranty_expired'])
            response['is_warranty_expired'] = True
        
        return response


