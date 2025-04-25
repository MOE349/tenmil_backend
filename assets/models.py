from django.db import models
from django.utils.translation import gettext_lazy as _

from configurations.base_features.db.base_model import BaseModel

class Category(BaseModel):
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), null=True, blank=True)
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class EquipmentCategory(Category):
    pass


class AttachmentCategory(Category):
    pass


class Asset(BaseModel):
    code = models.CharField(_("Code"), max_length=255, unique=True)
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), null=True, blank=True)
    location = models.ForeignKey('company.Location', on_delete=models.CASCADE)
    make = models.CharField(_("Make"), max_length=255, null=True, blank=True)
    model = models.CharField(_("Model"), max_length=255, null=True, blank=True)
    serial_number = models.CharField(_("Serial Number"), max_length=255, null=True, blank=True)
    purchase_date = models.DateField(_("Purchase Date"), auto_now_add=True)
    is_online = models.BooleanField(_("Is Online"), default=True)


    def __str__(self):
        return self.code


class Equipment(Asset):
    category = models.ForeignKey(EquipmentCategory, on_delete=models.CASCADE)


class Attachment(Asset):
    equipment_id = models.ForeignKey(Equipment, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(AttachmentCategory, on_delete=models.CASCADE)



