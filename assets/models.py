from django.db import models
from django.utils.translation import gettext_lazy as _

from assets.managers import AssetManager
from configurations.base_features.db.base_model import BaseModel

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation
from tenant_users.models import TenantUser
from projects.models import Project, AccountCode, JobCode, AssetStatus

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
    year = models.IntegerField(_("Year"), null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_projects")
    account_code = models.ForeignKey(AccountCode, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_account_codes")
    job_code = models.ForeignKey(JobCode, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_job_codes")
    asset_status = models.ForeignKey(AssetStatus, on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_asset_statuses")


    objects = AssetManager()

    # Image field - references one of the uploaded files as the main asset image
    image = models.ForeignKey(
        "file_uploads.FileUpload",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_as_image",
        help_text="Main image for this asset (must be one of the uploaded files)"
    )

    # Generic Relations
    gr_params = {
        "content_type_field":"content_type",
        "object_id_field":"object_id",
        "related_query_name":"asset"
    }
    capital_costs = GenericRelation("financial_reports.CapitalCost", **gr_params)
    meter_readings = GenericRelation("meter_readings.MeterReading", **gr_params)
    work_orders = GenericRelation("work_orders.WorkOrder", **gr_params)
    pm_settings = GenericRelation("pm_automation.PMSettings", **gr_params)
    
    # Files relation - for all file attachments
    files = GenericRelation(
        "file_uploads.FileUpload",
        content_type_field='content_type_ref',
        object_id_field='object_id',
        related_query_name='asset'
    )



    class Meta:
        abstract = True

    def __str__(self):
        return f"[{self.code}] {self.name}"
    
    def get_image_files(self):
        """Get all image files uploaded for this asset"""
        return self.files.not_deleted().images()
    
    def get_all_files(self):
        """Get all files uploaded for this asset (excluding deleted)"""
        return self.files.not_deleted()
    
    def set_image(self, file_upload):
        """
        Set the main image for this asset.
        Validates that the file belongs to this asset and is an image.
        """
        if file_upload is None:
            self.image = None
            self.save(update_fields=['image'])
            return True
            
        # Validate that the file belongs to this asset
        if not self.files.filter(id=file_upload.id).exists():
            raise ValueError("File must be uploaded for this asset first")
        
        # Validate that the file is an image
        if not file_upload.is_image():
            raise ValueError("File must be an image")
        
        # Validate that the file is not deleted
        if file_upload.is_deleted:
            raise ValueError("Cannot use deleted file as image")
        
        self.image = file_upload
        self.save(update_fields=['image'])
        return True
    
    def get_image_url(self):
        """Get the URL for the asset's main image"""
        if self.image and not self.image.is_deleted:
            return self.image.get_file_url()
        return None

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


