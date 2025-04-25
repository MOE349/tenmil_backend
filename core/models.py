from django.db import models

from django_tenants.models import TenantMixin, DomainMixin
from configurations.base_features.db.base_model import BaseModel


class Tenant(TenantMixin, BaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField()
    auto_create_schema = True
    paid_until = models.DateField(null=True, blank=True)
    on_trial = models.BooleanField(default=True)


class Domain(DomainMixin, BaseModel):
    pass

class WorkOrderStatusControls(BaseModel):
    name = models.CharField(max_length=50)
