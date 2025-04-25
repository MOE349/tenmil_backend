from configurations.base_features.db.base_model import BaseModel
from django.db import models
from django.utils.translation import gettext_lazy as _


class Site(BaseModel):
    name = models.CharField(_("Name"), max_length=255)
    code = models.CharField(_("Code"), max_length=6)

    def __str__(self):
        return self.name


class Location(BaseModel):
    name = models.CharField(_("Name"), max_length=255)
    site = models.ForeignKey(
        Site, on_delete=models.CASCADE, verbose_name=_("Site"))
    address = models.CharField(
        _("Address"), max_length=255, null=True, blank=True)
    slug = models.CharField(_("Slug"), max_length=255)

    def __str__(self):
        return self.name
