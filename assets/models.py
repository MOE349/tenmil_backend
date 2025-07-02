from django.db import models
from django.utils.translation import gettext_lazy as _

from assets.managers import AssetManager
from configurations.base_features.db.base_model import BaseModel

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation
from tenant_users.models import TenantUser

class Category(BaseModel):
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    description = models.TextField(_("Description"), blank=True, null=True)

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
    description = models.TextField(_("Description"), blank=True, null=True)
    make = models.CharField(_("Make"), max_length=255, blank=True, null=True)
    model = models.CharField(_("Model"), max_length=255, blank=True, null=True)
    serial_number = models.CharField(_("Serial Number"), max_length=255, blank=True, null=True)
    purchase_date = models.DateField(_("Purchase Date"), null=True, blank=True)
    is_online = models.BooleanField(_("Is Online"), default=True)
    location = models.ForeignKey("company.Location", on_delete=models.CASCADE)

    objects = AssetManager()

    # Generic Relations
    gr_params = {
        "content_type_field":"content_type",
        "object_id_field":"object_id",
        "related_query_name":"asset"
    }
    capital_costs = GenericRelation("financial_reports.CapitalCost", **gr_params)
    meter_readings = GenericRelation("meter_readings.MeterReading", **gr_params)
    scheduled_maintenances = GenericRelation("scheduled_maintenance.ScheduledMaintenance", **gr_params)
    work_orders = GenericRelation("work_orders.WorkOrder", **gr_params)



    class Meta:
        abstract = True

    def __str__(self):
        return f"[{self.code}] {self.name}"

class Equipment(Asset):
    category = models.ForeignKey(EquipmentCategory, on_delete=models.PROTECT, related_name="equipment")

    
class Attachment(Asset):
    category = models.ForeignKey(AttachmentCategory, on_delete=models.PROTECT, related_name="attachments")
    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="attached_attachments"
    )


class AssetMovementLog(BaseModel):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    asset = GenericForeignKey("content_type", "object_id")

    from_location = models.ForeignKey(
        "company.Location", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    to_location = models.ForeignKey(
        "company.Location", null=True, blank=True, on_delete=models.SET_NULL, related_name="incoming_movements"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    moved_by = models.ForeignKey(
        TenantUser,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="asset_movements",
        verbose_name=_("Moved By")
    )

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.asset} moved to {self.to_location} @ {self.timestamp}"


class AttachmentCompatibility(BaseModel):
    equipment_category = models.ForeignKey(
        EquipmentCategory, on_delete=models.CASCADE, related_name="compatible_attachments"
    )
    attachment_category = models.ForeignKey(
        AttachmentCategory, on_delete=models.CASCADE, related_name="compatible_equipments"
    )

    class Meta:
        unique_together = ("equipment_category", "attachment_category")

    def __str__(self):
        return f"{self.attachment_category} ⇄ {self.equipment_category}"
