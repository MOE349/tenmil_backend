from django.db import models

from configurations.base_features.db.base_model import BaseModel
from core.models import WorkOrderStatusControls
from users.models import User


class WorkOrderStatusNames(BaseModel):
    name = models.CharField(max_length=50)
    control = models.ForeignKey("core.WorkOrderStatusControls", on_delete=models.CASCADE)


class WorkOrder(BaseModel):
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE)
    status = models.ForeignKey(WorkOrderStatusNames, on_delete=models.CASCADE)
    maint_type = models.CharField(max_length=50)
    priority = models.CharField(max_length=50)
    suggested_start_date = models.DateField(null=True, blank=True)
    completion_end_date = models.DateField(null=True, blank=True)
    description = models.TextField()
    is_closed = models.BooleanField(default=False)
    

       

class WorkOrderChecklist(BaseModel):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE)
    description = models.TextField(null=True, blank=True)

    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name="WorkOrderChecklist_AssignedTo", null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    hrs_estimated = models.IntegerField(null=True, blank=True)
    
    completed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="WorkOrderChecklist_CompletedBy", null=True, blank=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    hrs_spent = models.IntegerField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)


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
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE)
    completion_notes = models.TextField()
    problem = models.TextField(null=True, blank=True)
    root_cause = models.TextField(null=True, blank=True)
    solution = models.TextField(null=True, blank=True)
    admin_notes = models.TextField(null=True, blank=True)

