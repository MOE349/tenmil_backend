from configurations.base_features.db.base_model import BaseModel
from django.db import models
from django.utils.translation import gettext_lazy as _


class Site(BaseModel):
    name = models.CharField(_("Name"), max_length=255)
    code = models.CharField(_("Code"), max_length=6, unique=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Location(BaseModel):
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    address = models.CharField(_("Address"), max_length=255, blank=True, null=True)
    site = models.ForeignKey(Site, related_name="locations", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} @ {self.site.name}"
