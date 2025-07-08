from configurations.base_features.db.base_model import BaseModel
from django.db import models

from configurations.base_features.db.db_choices import TriggerTypeChoices

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class SmIttirationCycleChecklist(BaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    class Meta:
        db_table = "scheduled_maintenance_smittirationcyclechecklist"


class ScheduledMaintenance(BaseModel):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    asset = GenericForeignKey("content_type", "object_id")
    trigger_type = models.CharField(max_length=50, choices=TriggerTypeChoices.choices, default=TriggerTypeChoices.METER_READING)
    trigger_at = models.JSONField(default=dict)
    starting_at = models.DateField()


class SmIttirationCycle(BaseModel):
    ittiration = models.IntegerField(default=500)
    scheduled_maintenance = models.ForeignKey(ScheduledMaintenance, on_delete=models.CASCADE)
    checklist = models.ManyToManyField('scheduled_maintenance.SmIttirationCycleChecklist', blank=True)
    # parts = models.ManyToManyField('parts.Parts')


class SmLog(BaseModel):
    pass
