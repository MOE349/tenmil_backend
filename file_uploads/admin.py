from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import FileUpload


@admin.register(FileUpload)
class FileUploadAdmin(admin.ModelAdmin):
    list_display = [
        'original_filename', 'content_type', 'file_size_display', 
        'uploaded_by', 'validation_status', 'access_level', 
        'is_deleted', 'created_at'
    ]
    list_filter = [
        'validation_status', 'access_level', 'is_deleted', 
        'content_type', 'created_at'
    ]
    search_fields = ['original_filename', 'description', 'tags', 'file_hash']
    readonly_fields = [
        'id', 'file_size', 'content_type', 'file_hash', 
        'created_at', 'updated_at', 'file_link'
    ]
    fieldsets = (
        ('File Information', {
            'fields': ('id', 'file', 'file_link', 'original_filename', 'file_size', 'content_type', 'file_hash')
        }),
        ('Metadata', {
            'fields': ('description', 'tags', 'uploaded_by')
        }),
        ('Validation', {
            'fields': ('is_validated', 'validation_status', 'validation_errors')
        }),
        ('Access Control', {
            'fields': ('is_public', 'access_level')
        }),
        ('Generic Relations', {
            'fields': ('content_type_ref', 'object_id'),
            'classes': ('collapse',)
        }),
        ('Deletion', {
            'fields': ('is_deleted', 'deleted_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        """Display file size in human readable format"""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    file_size_display.short_description = 'Size'
    
    def file_link(self, obj):
        """Display link to download the file"""
        if obj.file:
            url = obj.get_download_url()
            return format_html('<a href="{}" target="_blank">Download</a>', url)
        return "No file"
    file_link.short_description = 'Download'
    
    def get_queryset(self, request):
        """Include soft-deleted files in admin"""
        return self.model.objects.all()
    
    actions = ['mark_as_validated', 'mark_as_failed', 'soft_delete', 'restore_files']
    
    def mark_as_validated(self, request, queryset):
        """Mark selected files as validated"""
        updated = queryset.update(is_validated=True, validation_status='passed')
        self.message_user(request, f'{updated} files marked as validated.')
    mark_as_validated.short_description = 'Mark selected files as validated'
    
    def mark_as_failed(self, request, queryset):
        """Mark selected files as validation failed"""
        updated = queryset.update(is_validated=False, validation_status='failed')
        self.message_user(request, f'{updated} files marked as validation failed.')
    mark_as_failed.short_description = 'Mark selected files as validation failed'
    
    def soft_delete(self, request, queryset):
        """Soft delete selected files"""
        from django.utils import timezone
        updated = queryset.update(is_deleted=True, deleted_at=timezone.now())
        self.message_user(request, f'{updated} files soft deleted.')
    soft_delete.short_description = 'Soft delete selected files'
    
    def restore_files(self, request, queryset):
        """Restore soft-deleted files"""
        updated = queryset.update(is_deleted=False, deleted_at=None)
        self.message_user(request, f'{updated} files restored.')
    restore_files.short_description = 'Restore selected files'