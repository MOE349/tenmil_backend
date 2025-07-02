from assets.models import Asset
from configurations.base_features.db.base_model import BaseModel
from django.db import models
from django.utils.translation import gettext_lazy as _

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class CapitalCost(BaseModel):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    asset = GenericForeignKey("content_type", "object_id")
    purchase_cost = models.FloatField(_("Purchase Cost"), default=1)
    resale_cost = models.FloatField(_("Resale Cost Low Sev"), default=1)
    finance_years = models.IntegerField(_("FINANCE YEARS"), default=1)
    interest_rate = models.FloatField(_("Interest rate"), default=1)
    expected_hours = models.IntegerField(_("Expected Hours"), default=1)
    operational_cost_per_year = models.FloatField(_("Operational Cost"), default=1)
    capital_work_cost = models.FloatField(_("Capital Work Cost"), default=1)

    class Meta:
        unique_together = ("content_type", "object_id")
