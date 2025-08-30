from configurations.base_features.db.base_model import BaseModel
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class Vendor(BaseModel):
    """Vendor model for managing supplier information"""
    name = models.CharField(_("Name"), max_length=255)
    code = models.CharField(_("Code"), max_length=50, unique=True)
    
    # Address fields
    country = models.CharField(_("Country"), max_length=100, blank=True, null=True)
    city = models.CharField(_("City"), max_length=100, blank=True, null=True)
    province_state = models.CharField(_("Province/State"), max_length=100, blank=True, null=True)
    postal_code_zip = models.CharField(_("Postal Code/ZIP"), max_length=20, blank=True, null=True)
    address = models.CharField(_("Address"), max_length=255, blank=True, null=True)
    
    # Auto-filled full address
    full_address = models.TextField(_("Full Address"), blank=True, null=True, editable=False)
    
    # Optional notes
    notes = models.TextField(_("Notes"), blank=True, null=True)

    class Meta:
        verbose_name = _("Vendor")
        verbose_name_plural = _("Vendors")
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        """Override save to auto-generate full_address"""
        self.full_address = self._generate_full_address()
        super().save(*args, **kwargs)

    def _generate_full_address(self):
        """Generate full address from individual address components"""
        address_parts = []
        
        if self.address:
            address_parts.append(self.address)
        if self.city:
            address_parts.append(self.city)
        if self.province_state:
            address_parts.append(self.province_state)
        if self.postal_code_zip:
            address_parts.append(self.postal_code_zip)
        if self.country:
            address_parts.append(self.country)
            
        return ', '.join(address_parts) if address_parts else ''


class ContactPersonnel(BaseModel):
    """Contact personnel for vendors"""
    full_name = models.CharField(_("Full Name"), max_length=255)
    email = models.EmailField(_("Email"))
    phone_number = models.CharField(_("Phone Number"), max_length=20, blank=True, null=True)
    
    # Foreign key to Vendor
    vendor = models.ForeignKey(
        Vendor, 
        related_name="contact_personnel", 
        on_delete=models.CASCADE,
        verbose_name=_("Vendor")
    )
    
    # Primary contact flag - only one per vendor
    is_primary = models.BooleanField(_("Is Primary Contact"), default=False)

    class Meta:
        verbose_name = _("Contact Personnel")
        verbose_name_plural = _("Contact Personnel")
        ordering = ['-is_primary', 'full_name']

    def __str__(self):
        primary_indicator = " (Primary)" if self.is_primary else ""
        return f"{self.full_name}{primary_indicator} - {self.vendor.name}"

    def clean(self):
        """Validate that only one primary contact exists per vendor"""
        if self.is_primary:
            # Check if another primary contact exists for this vendor
            existing_primary = ContactPersonnel.objects.filter(
                vendor=self.vendor,
                is_primary=True
            ).exclude(pk=self.pk)
            
            if existing_primary.exists():
                raise ValidationError({
                    'is_primary': _('Only one primary contact is allowed per vendor.')
                })

    def save(self, *args, **kwargs):
        """Override save to handle primary contact logic"""
        # If this is the first contact for the vendor, make it primary
        if not self.pk and not ContactPersonnel.objects.filter(vendor=self.vendor).exists():
            self.is_primary = True
        
        # If setting as primary, unset other primary contacts for this vendor
        if self.is_primary:
            ContactPersonnel.objects.filter(
                vendor=self.vendor,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        
        # Run clean validation
        self.clean()
        super().save(*args, **kwargs)


