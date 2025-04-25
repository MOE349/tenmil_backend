from assets.models import Asset
from configurations.base_features.constants import User
from configurations.base_features.db.base_model import BaseModel
from django.db import models

class MeterReading(BaseModel):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    meter_reading = models.FloatField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.asset.name} - {self.meter_reading}"


