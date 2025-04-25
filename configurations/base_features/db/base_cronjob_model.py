from django.db import models

from configurations.base_features.db.base_model import BaseModel


class BaseCronJobModel(BaseModel):

    TRIGGER_TYPE_CHOICES = (
        ("interval", "Interval"),
        ("cron", "Cron"),
        ("date", "Date"),
    )

    trigger_type = models.CharField(
        max_length=255, choices=TRIGGER_TYPE_CHOICES)
    trigger_args = models.JSONField()
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
