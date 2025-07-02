from assets.services import move_asset
from assets.models import *
from django.contrib import admin

from company.models import Location


admin.site.register(Attachment)
admin.site.register(EquipmentCategory)
admin.site.register(AttachmentCategory)

class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0
    fk_name = 'equipment'  # ensures only this FK is used
    fields = ("code", "name", "category", "location")


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "location")
    inlines = [AttachmentInline]


def move_selected_assets(modeladmin, request, queryset):
    location_id = request.POST.get("new_location_id")
    location = Location.objects.get(id=location_id)
    for asset in queryset:
        move_asset(asset, location, notes=f"Bulk moved by {request.user}")

move_selected_assets.short_description = "Move selected assets to a location"
