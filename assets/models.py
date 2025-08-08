from django.db import models
from django.utils.translation import gettext_lazy as _

from assets.managers import AssetManager
from configurations.base_features.db.base_model import BaseModel
from configurations.mixins.file_attachment_mixins import FileAttachmentMixin

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation
from tenant_users.models import TenantUser
from projects.models import Project, AccountCode, JobCode, AssetStatus
from work_orders.models import *

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

class AssetWeightClass(BaseModel):
    name = models.CharField(_("Name"), max_length=255)
    weight = models.CharField(_("Weight"))

    class Meta:
        abstract = True

class EquipmentWeightClass(AssetWeightClass):
    pass
    

class Asset(FileAttachmentMixin, BaseModel):
    code = models.CharField(_("Code"), max_length=255, unique=True)
    name = models.CharField(_("Name"), max_length=255)
    description = models.TextField(_("Description"), blank=True, null=True)
    make = models.CharField(_("Make"), max_length=255, blank=True, null=True)
    model = models.CharField(_("Model"), max_length=255, blank=True, null=True)
    serial_number = models.CharField(_("Serial Number"), max_length=255, blank=True, null=True)
    purchase_date = models.DateField(_("Purchase Date"), null=True, blank=True)
    is_online = models.BooleanField(_("Is Online"), default=True)
    location = models.ForeignKey("company.Location", on_delete=models.CASCADE)
    year = models.IntegerField(_("Year"), null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_projects")
    account_code = models.ForeignKey(AccountCode, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_account_codes")
    job_code = models.ForeignKey(JobCode, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_job_codes")
    asset_status = models.ForeignKey(AssetStatus, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_asset_statuses")

    objects = AssetManager()

    # Generic Relations (keeping existing asset relations)
    gr_params = {
        "content_type_field":"content_type",
        "object_id_field":"object_id",
        "related_query_name":"asset"
    }
    capital_costs = GenericRelation("financial_reports.CapitalCost", **gr_params)
    meter_readings = GenericRelation("meter_readings.MeterReading", **gr_params)
    work_orders = GenericRelation("work_orders.WorkOrder", **gr_params)
    pm_settings = GenericRelation("pm_automation.PMSettings", **gr_params)
    
    # FileAttachmentMixin automatically provides:
    # - image: ForeignKey for main image
    # - files: GenericRelation for all file attachments  
    # - Helper methods: get_image_files(), get_all_files(), get_documents(), set_image(), get_image_url()

    class Meta:
        abstract = True

    def __str__(self):
        return f"[{self.code}] {self.name}"

class Equipment(Asset):
    category = models.ForeignKey(EquipmentCategory, on_delete=models.PROTECT, related_name="equipment")
    weight_class = models.ForeignKey(EquipmentWeightClass, on_delete=models.SET_NULL, related_name="equipment", null=True, blank=True)

    
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



class AssetOnlineStatusLog(BaseModel):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    asset = GenericForeignKey("content_type", "object_id")

    offline_user = models.ForeignKey(
        TenantUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="asset_offline_logs",
    )

    online_user = models.ForeignKey(
        TenantUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="asset_online_logs",
    )

    # Only set when the asset becomes offline via Work Order action
    work_order = models.ForeignKey(
        'work_orders.WorkOrder',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="asset_online_status_logs"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Asset {self.object_id} offline_by={getattr(self.offline_user, 'id', None)} online_by={getattr(self.online_user, 'id', None)}"

