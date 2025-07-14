from configurations.base_features.db.base_model import BaseModel
from django.db import models
from tenant_users.models import TenantUser as User

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class MeterReading(BaseModel):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    asset = GenericForeignKey("content_type", "object_id")
    meter_reading = models.FloatField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        try:
            asset_name = self.asset.name if self.asset else f"{self.content_type.app_label}.{self.content_type.model}.{self.object_id}"
            return f"{asset_name} - {self.meter_reading}"
        except Exception:
            return f"{self.content_type.app_label}.{self.content_type.model}.{self.object_id} - {self.meter_reading}"


