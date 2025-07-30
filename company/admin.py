from company.models import *
from django.contrib import admin


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ('language', 'timezone', 'currency', 'created_at', 'updated_at')
    fields = ('language', 'timezone', 'currency')
    
    def has_add_permission(self, request):
        # Only allow one CompanyProfile per tenant
        return not CompanyProfile.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of CompanyProfile
        return False


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'timezone', 'get_effective_timezone_name', 'created_at')
    list_filter = ('timezone',)
    fields = ('name', 'code', 'timezone')
    
    def get_effective_timezone_name(self, obj):
        return obj.get_effective_timezone_name()
    get_effective_timezone_name.short_description = 'Effective Timezone'


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'site', 'get_effective_timezone_name', 'created_at')
    list_filter = ('site',)
    fields = ('name', 'slug', 'address', 'site')
    
    def get_effective_timezone_name(self, obj):
        return obj.get_effective_timezone_name()
    get_effective_timezone_name.short_description = 'Effective Timezone'
