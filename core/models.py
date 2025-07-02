from django.db import models

from django_tenants.models import TenantMixin, DomainMixin
from configurations.base_features.db.base_model import BaseModel


class Tenant(TenantMixin, BaseModel):
    name = models.CharField(max_length=100)
    description = models.TextField()
    auto_create_schema = True
    paid_until = models.DateField(null=True, blank=True)
    on_trial = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name


class Domain(DomainMixin, BaseModel):
    def __str__(self):
        return self.domain

class WorkOrderStatusControls(BaseModel):
    key = models.SlugField(max_length=50, unique=True)  # e.g., "in_progress"
    name = models.CharField(max_length=100)             # e.g., "In Progress"
    color = models.CharField(max_length=20, null=True, blank=True)  # optional UI color
    order = models.PositiveSmallIntegerField(default=0)  # display/order priority
    
    
    def __str__(self):
        return self.name
