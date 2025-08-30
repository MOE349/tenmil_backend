from vendors.models import *
from django.contrib import admin
from django.utils.html import format_html


class ContactPersonnelInline(admin.TabularInline):
    """Inline admin for ContactPersonnel within Vendor admin"""
    model = ContactPersonnel
    extra = 1
    fields = ('full_name', 'email', 'phone_number', 'is_primary')
    readonly_fields = ()


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'code', 
        'city', 
        'province_state', 
        'country',
        'get_contact_count',
        'get_primary_contact',
        'created_at'
    )
    list_filter = ('country', 'province_state', 'city', 'created_at')
    search_fields = ('name', 'code', 'city', 'country', 'notes')
    readonly_fields = ('full_address', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'notes')
        }),
        ('Address Information', {
            'fields': (
                'address', 
                'city', 
                'province_state', 
                'postal_code_zip', 
                'country',
                'full_address'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [ContactPersonnelInline]
    
    def get_contact_count(self, obj):
        """Display number of contacts for this vendor"""
        count = obj.contact_personnel.count()
        return format_html(
            '<span style="color: {};">{}</span>',
            'green' if count > 0 else 'red',
            count
        )
    get_contact_count.short_description = 'Contacts'
    
    def get_primary_contact(self, obj):
        """Display primary contact for this vendor"""
        primary = obj.contact_personnel.filter(is_primary=True).first()
        if primary:
            return format_html(
                '<strong>{}</strong><br/><small>{}</small>',
                primary.full_name,
                primary.email
            )
        return format_html('<span style="color: red;">No primary contact</span>')
    get_primary_contact.short_description = 'Primary Contact'


@admin.register(ContactPersonnel)
class ContactPersonnelAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 
        'email', 
        'phone_number',
        'vendor',
        'is_primary_display',
        'created_at'
    )
    list_filter = ('is_primary', 'vendor', 'created_at')
    search_fields = ('full_name', 'email', 'phone_number', 'vendor__name', 'vendor__code')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('full_name', 'email', 'phone_number')
        }),
        ('Vendor Association', {
            'fields': ('vendor', 'is_primary')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def is_primary_display(self, obj):
        """Display primary status with styling"""
        if obj.is_primary:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Primary</span>'
            )
        return format_html('<span style="color: gray;">Secondary</span>')
    is_primary_display.short_description = 'Status'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Customize vendor field in admin"""
        if db_field.name == "vendor":
            kwargs["queryset"] = Vendor.objects.order_by('name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
