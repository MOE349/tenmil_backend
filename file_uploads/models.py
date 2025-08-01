import os
import uuid
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from configurations.base_features.db.base_model import BaseModel
from configurations.base_features.db.base_manager import BaseManager
from tenant_users.models import TenantUser as User


def get_upload_path(instance, filename):
    """
    Generate upload path with date-based folder structure and UUID filename
    """
    # Get file extension
    ext = filename.split('.')[-1].lower()
    
    # Generate UUID filename
    uuid_filename = f"{uuid.uuid4()}.{ext}"
    
    # Create date-based path: YYYY/MM/DD/
    from datetime import datetime
    now = datetime.now()
    date_path = now.strftime('%Y/%m/%d')
    
    return f"uploads/{date_path}/{uuid_filename}"


class FileUpload(BaseModel):
    """
    Centralized file upload model for handling all file operations
    """
    
    # File storage fields
    file = models.FileField(
        upload_to=get_upload_path,
        help_text="The uploaded file"
    )
    original_filename = models.CharField(
        max_length=255,
        help_text="Original filename as uploaded by user"
    )
    file_size = models.PositiveBigIntegerField(
        help_text="File size in bytes"
    )
    content_type = models.CharField(
        max_length=100,
        help_text="MIME type of the file"
    )
    file_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="SHA-256 hash for file integrity"
    )
    
    # Metadata fields
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of the file"
    )
    tags = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Comma-separated tags for categorization"
    )
    
    # Validation and status fields
    is_validated = models.BooleanField(
        default=False,
        help_text="Whether the file has passed validation"
    )
    validation_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('passed', 'Passed'),
            ('failed', 'Failed'),
            ('quarantined', 'Quarantined'),
        ],
        default='pending',
        help_text="Status of file validation"
    )
    validation_errors = models.JSONField(
        default=list,
        blank=True,
        help_text="List of validation errors if any"
    )
    
    # User and access fields
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_files'
    )
    is_public = models.BooleanField(
        default=False,
        help_text="Whether the file is publicly accessible"
    )
    access_level = models.CharField(
        max_length=20,
        choices=[
            ('private', 'Private'),
            ('tenant', 'Tenant Level'),
            ('public', 'Public'),
        ],
        default='tenant',
        help_text="Access level for the file"
    )
    
    # Generic relation fields for linking to any model
    content_type_ref = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Type of the model this file is attached to"
    )
    object_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of the object this file is attached to"
    )
    content_object = GenericForeignKey('content_type_ref', 'object_id')
    
    # Soft delete support
    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag"
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the file was soft deleted"
    )
    
    class Meta:
        db_table = 'file_uploads'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type_ref', 'object_id']),
            models.Index(fields=['uploaded_by']),
            models.Index(fields=['is_deleted']),
            models.Index(fields=['validation_status']),
            models.Index(fields=['file_hash']),
        ]
    
    def __str__(self):
        return f"{self.original_filename} ({self.file_size} bytes)"
    
    def save(self, *args, **kwargs):
        """Override save to set file metadata"""
        if self.file and not self.file_size:
            self.file_size = self.file.size
            
        if self.file and not self.original_filename:
            self.original_filename = self.file.name
            
        if self.file and not self.content_type:
            import mimetypes
            self.content_type = mimetypes.guess_type(self.file.name)[0] or 'application/octet-stream'
            
        super().save(*args, **kwargs)
    
    def delete(self, hard_delete=False, *args, **kwargs):
        """
        Soft delete by default, hard delete if specified
        """
        if hard_delete:
            # Delete the actual file
            if self.file and os.path.isfile(self.file.path):
                os.remove(self.file.path)
            super().delete(*args, **kwargs)
        else:
            # Soft delete
            from django.utils import timezone
            self.is_deleted = True
            self.deleted_at = timezone.now()
            self.save()
    
    def get_file_url(self):
        """Get the URL for accessing the file"""
        if self.file:
            return self.file.url
        return None
    
    def get_download_url(self):
        """Get the URL for downloading the file with proper headers"""
        from django.urls import reverse
        return reverse('file_uploads:file-download', kwargs={'pk': self.pk})
    
    def is_image(self):
        """Check if the file is an image"""
        image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml']
        return self.content_type in image_types
    
    def is_document(self):
        """Check if the file is a document"""
        doc_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/plain',
            'text/csv'
        ]
        return self.content_type in doc_types
    
    def generate_file_hash(self):
        """Generate SHA-256 hash of the file"""
        if self.file:
            import hashlib
            hash_sha256 = hashlib.sha256()
            
            with self.file.open('rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            
            self.file_hash = hash_sha256.hexdigest()
            return self.file_hash
        return None


class FileUploadQuerySet(models.QuerySet):
    """Custom QuerySet for FileUpload with chainable methods"""
    
    def not_deleted(self):
        """Return only non-deleted files"""
        return self.filter(is_deleted=False)
    
    def validated(self):
        """Return only validated files"""
        return self.filter(validation_status='passed', is_validated=True)
    
    def for_object(self, obj):
        """Get files for a specific object"""
        from django.contrib.contenttypes.models import ContentType
        content_type = ContentType.objects.get_for_model(obj)
        return self.filter(content_type_ref=content_type, object_id=obj.pk)
    
    def images(self):
        """Return only image files"""
        image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml']
        return self.filter(content_type__in=image_types)
    
    def documents(self):
        """Return only document files"""
        doc_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/plain',
            'text/csv'
        ]
        return self.filter(content_type__in=doc_types)


class FileUploadManager(BaseManager):
    """Custom manager for FileUpload"""
    
    def get_queryset(self):
        """Return custom QuerySet with our methods"""
        return FileUploadQuerySet(self.model, using=self._db)
    
    def not_deleted(self):
        """Return only non-deleted files"""
        return self.get_queryset().not_deleted()
    
    def validated(self):
        """Return only validated files"""
        return self.get_queryset().validated()
    
    def for_object(self, obj):
        """Get files for a specific object"""
        return self.get_queryset().for_object(obj)
    
    def images(self):
        """Return only image files"""
        return self.get_queryset().images()
    
    def documents(self):
        """Return only document files"""
        return self.get_queryset().documents()


# Add the custom manager to the model
FileUpload.add_to_class('objects', FileUploadManager())