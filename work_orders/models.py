from django.db import models

from configurations.base_features.db.base_model import BaseModel
from tenant_users.models import TenantUser as User

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class WorkOrderStatusNames(BaseModel):
    name = models.CharField(max_length=50, unique=True)
    control = models.ForeignKey("core.WorkOrderStatusControls", on_delete=models.CASCADE)
    is_system_level = models.BooleanField(default=False)


class WorkOrder(BaseModel):
    code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    asset = GenericForeignKey("content_type", "object_id")
    status = models.ForeignKey(WorkOrderStatusNames, on_delete=models.PROTECT)
    maint_type = models.CharField(max_length=50,null=True, blank=True)
    priority = models.CharField(max_length=50,null=True, blank=True)
    suggested_start_date = models.DateField(null=True, blank=True)
    completion_end_date = models.DateField(null=True, blank=True)
    suggested_completion_date = models.DateField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)
    is_auto_generated = models.BooleanField(default=False)
    is_reopened = models.BooleanField(default=False)
    completion_meter_reading = models.IntegerField(null=True, blank=True)
    trigger_meter_reading = models.IntegerField(null=True, blank=True)

    def save(self, *args, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.code:
            self.code = f"WO_{WorkOrder.objects.count() + 1}"
        return super().save(*args, force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)
    

class WorkOrderChecklist(BaseModel):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE)
    description = models.TextField(null=True, blank=True)    
    completed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="WorkOrderChecklist_CompletedBy", null=True, blank=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    hrs_spent = models.IntegerField(null=True, blank=True)


class WorkOrderMiscCost(BaseModel):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()


class WorkOrderLog(BaseModel):
    class LogTypeChoices(models.TextChoices):
        CREATED = 'Created'
        REOPENED = "Reopened"
        UPDATED = 'Updated'
        COMPLETED = 'Closed'
        CANCELLED = 'Cancelled'
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    log_type = models.CharField(max_length=50, choices=LogTypeChoices.choices)


class WorkOrderCompletionNote(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    work_order = models.OneToOneField(WorkOrder, on_delete=models.CASCADE)
    completion_notes = models.TextField(null=True, blank=True)
    problem = models.TextField(null=True, blank=True)
    root_cause = models.TextField(null=True, blank=True)
    solution = models.TextField(null=True, blank=True)
    admin_notes = models.TextField(null=True, blank=True)

