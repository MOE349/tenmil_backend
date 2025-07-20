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
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='account_codes')
    name = models.CharField(_("Name"), max_length=255)
    
    class Meta:
        verbose_name = _("Account Code")
        verbose_name_plural = _("Account Codes")
    
    def __str__(self):
        return f"{self.name} ({self.project.name})"


class JobCode(BaseModel):
    account_code = models.ForeignKey(AccountCode, on_delete=models.CASCADE, related_name='job_codes')
    name = models.CharField(_("Name"), max_length=255)
    
    class Meta:
        verbose_name = _("Job Code")
        verbose_name_plural = _("Job Codes")
    
    def __str__(self):
        return f"{self.name} ({self.account_code.name})"


class AssetStatus(BaseModel):
    job_code = models.ForeignKey(JobCode, on_delete=models.CASCADE, related_name='asset_statuses')
    name = models.CharField(_("Name"), max_length=255)
    
    class Meta:
        verbose_name = _("Asset Status")
        verbose_name_plural = _("Asset Statuses")
    
    def __str__(self):
        return f"{self.name} ({self.job_code.name})"


