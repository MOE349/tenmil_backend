from configurations.base_features.db.base_model import BaseModel
from django.db import models
from django.utils.translation import gettext_lazy as _


class Project(BaseModel):
    name = models.CharField(_("Name"), max_length=255)
    
    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")
    
    def __str__(self):
        return self.name


class AccountCode(BaseModel):
    name = models.CharField(_("Name"), max_length=255)
    
    class Meta:
        verbose_name = _("Account Code")
        verbose_name_plural = _("Account Codes")
    
    def __str__(self):
        return self.name


class JobCode(BaseModel):
    name = models.CharField(_("Name"), max_length=255)
    
    class Meta:
        verbose_name = _("Job Code")
        verbose_name_plural = _("Job Codes")
    
    def __str__(self):
        return self.name


class AssetStatus(BaseModel):
    name = models.CharField(_("Name"), max_length=255)
    
    class Meta:
        verbose_name = _("Asset Status")
        verbose_name_plural = _("Asset Statuses")
    
    def __str__(self):
        return self.name


