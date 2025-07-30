from configurations.base_features.db.base_model import BaseModel
from django.db import models
from django.utils.translation import gettext_lazy as _
import pytz


class CompanyProfile(BaseModel):
    """Single record per tenant containing company-wide settings"""
    language = models.CharField(
        _("Language"), 
        max_length=10, 
        default='EN',
        help_text=_("Language code (e.g., EN, FR, ES)")
    )
    timezone = models.CharField(
        _("Timezone"), 
        max_length=50, 
        default='America/Denver',
        help_text=_("Timezone name (e.g., America/Denver, UTC, Europe/London)")
    )
    currency = models.CharField(
        _("Currency"), 
        max_length=10, 
        default='CAD',
        help_text=_("Currency code (e.g., CAD, USD, EUR)")
    )
    
    class Meta:
        verbose_name = _("Company Profile")
        verbose_name_plural = _("Company Profiles")
    
    def __str__(self):
        return f"Company Profile - {self.language}/{self.timezone}/{self.currency}"
    
    @classmethod
    def get_or_create_default(cls):
        """Get or create the company profile for this tenant"""
        profile, created = cls.objects.get_or_create(
            defaults={
                'language': 'EN',
                'timezone': 'America/Denver',
                'currency': 'CAD',
            }
        )
        return profile
    
    def get_timezone_object(self):
        """Get pytz timezone object"""
        try:
            return pytz.timezone(self.timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            # Fallback to UTC if timezone is invalid
            return pytz.UTC


class Site(BaseModel):
    name = models.CharField(_("Name"), max_length=255)
    code = models.CharField(_("Code"), max_length=6, unique=True)
    timezone = models.CharField(
        _("Timezone"), 
        max_length=50, 
        blank=True,
        null=True,
        help_text=_("Site-specific timezone (e.g., America/Denver, UTC). If not set, company timezone will be used.")
    )

    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def get_effective_timezone(self):
        """Get effective timezone for this site (site timezone or company timezone)"""
        if self.timezone:
            try:
                return pytz.timezone(self.timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                pass
        
        # Fallback to company timezone
        company_profile = CompanyProfile.get_or_create_default()
        return company_profile.get_timezone_object()
    
    def get_effective_timezone_name(self):
        """Get effective timezone name for this site"""
        if self.timezone:
            return self.timezone
        
        # Fallback to company timezone
        company_profile = CompanyProfile.get_or_create_default()
        return company_profile.timezone


class Location(BaseModel):
    name = models.CharField(_("Name"), max_length=255)
    slug = models.SlugField(_("Slug"), max_length=255, unique=True)
    address = models.CharField(_("Address"), max_length=255, blank=True, null=True)
    site = models.ForeignKey(Site, related_name="locations", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} @ {self.site.name}"
    
    def get_effective_timezone(self):
        """Get effective timezone for this location (from site)"""
        return self.site.get_effective_timezone()
    
    def get_effective_timezone_name(self):
        """Get effective timezone name for this location"""
        return self.site.get_effective_timezone_name()
