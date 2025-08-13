from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from configurations.base_features.db.base_model import BaseModel
from work_orders.models import WorkOrder


class Component(BaseModel):
    name = models.CharField(max_length=255)
    initial_meter_reading = models.IntegerField(default=0)
    work_order = models.ForeignKey(WorkOrder, on_delete=models.SET_NULL, related_name='components', null=True, blank=True)
    changed_at_meter_reading = models.IntegerField(default=0)
    
    # Generic foreign key to asset (Equipment or Attachment)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    asset = GenericForeignKey('content_type', 'object_id')
    
    # File uploads relation
    files = GenericRelation('file_uploads.FileUpload', content_type_field='content_type_ref', object_id_field='object_id')
    
    warranty_meter_reading = models.IntegerField(null=True, blank=True)
    warranty_exp_date = models.DateField(null=True, blank=True)
    is_warranty_expired = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.work_order}" if self.work_order else f"{self.name} - No Work Order"
    
    def save(self, *args, **kwargs):
        # Check warranty expiration before saving
        self.check_warranty_expiration()
        super().save(*args, **kwargs)
    
    def check_warranty_expiration(self):
        """Check if warranty has expired based on meter reading or date"""
        from django.utils import timezone
        
        # Get component meter reading for validation
        component_meter_reading = self.get_component_meter_reading()
        
        # Check meter reading warranty expiration
        if (self.warranty_meter_reading is not None and 
            component_meter_reading > self.warranty_meter_reading):
            self.is_warranty_expired = True
            
        # Check date warranty expiration
        if (self.warranty_exp_date is not None and 
            timezone.now().date() > self.warranty_exp_date):
            self.is_warranty_expired = True
    
    def get_component_meter_reading(self):
        """Calculate component meter reading as specified in requirements"""
        # Get asset's latest meter reading
        from meter_readings.models import MeterReading
        
        latest_meter_reading = MeterReading.objects.filter(
            content_type=self.content_type,
            object_id=self.object_id
        ).order_by('-created_at').first()
        
        asset_latest_reading = latest_meter_reading.meter_reading if latest_meter_reading else 0
        
        # Get work order completion meter reading if work order is closed
        wo_completion_reading = 0
        if self.work_order and self.work_order.is_closed and self.work_order.completion_meter_reading:
            wo_completion_reading = self.work_order.completion_meter_reading
            
        # Calculate: asset latest meter reading - work order completion meter reading (if closed) or 0 + initial meter reading
        if wo_completion_reading == 0 and self.changed_at_meter_reading == 0:
            component_meter_reading = self.initial_meter_reading

        elif wo_completion_reading == 0 and self.changed_at_meter_reading > 0:
            component_meter_reading = asset_latest_reading - self.changed_at_meter_reading + self.initial_meter_reading

        else:
            component_meter_reading = asset_latest_reading - wo_completion_reading + self.initial_meter_reading
        
        return component_meter_reading

    class Meta:
        indexes = [
            models.Index(fields=['work_order']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['is_warranty_expired']),
        ]


