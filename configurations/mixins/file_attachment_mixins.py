"""
Reusable mixins for adding file attachments to any model

Usage:
1. Add FileAttachmentMixin to your model
2. Add FileAttachmentSerializerMixin to your serializer  
3. Add FileAttachmentViewMixin to your view (if you want set-image functionality)
4. Run makemigrations and migrate
"""

from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from configurations.base_features.exceptions.base_exceptions import LocalBaseException


class FileAttachmentMixin(models.Model):
    """
    Mixin to add file attachment capabilities to any model
    
    Usage:
        class WorkOrder(FileAttachmentMixin, BaseModel):
            # your existing fields
            pass
    
    This adds:
    - files: GenericRelation to FileUpload
    - image: Optional main image field
    - Helper methods for file management
    """
    
    # Main image field (optional - can be None if you don't need images)
    image = models.ForeignKey(
        "file_uploads.FileUpload",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_as_image",
        help_text="Main image for this object (must be one of the uploaded files)"
    )
    
    # Files relation - for all file attachments
    files = GenericRelation(
        "file_uploads.FileUpload",
        content_type_field='content_type_ref',
        object_id_field='object_id',
        related_query_name='%(class)s'
    )
    
    @property
    def _files_manager(self):
        """Helper property to ensure we get the proper manager with QuerySet methods"""
        return self.files
    
    class Meta:
        abstract = True
    
    def get_image_files(self):
        """Get all image files uploaded for this object"""
        return self.files.not_deleted().images()
    
    def get_all_files(self):
        """Get all files uploaded for this object (excluding deleted)"""
        return self.files.not_deleted()
    
    def get_documents(self):
        """Get all document files uploaded for this object"""
        return self.files.not_deleted().documents()
    
    def set_image(self, file_upload):
        """
        Set the main image for this object.
        Validates that the file belongs to this object and is an image.
        """
        if file_upload is None:
            self.image = None
            self.save(update_fields=['image'])
            return True
            
        # Validate that the file belongs to this object
        if not self.files.filter(id=file_upload.id).exists():
            raise ValueError("File must be uploaded for this object first")
        
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
        """Get the URL for the object's main image"""
        if self.image and not self.image.is_deleted:
            return self.image.get_file_url()
        return None


class FileAttachmentSerializerMixin:
    """
    Mixin to add file information to serializer responses
    
    Usage:
        class WorkOrderBaseSerializer(FileAttachmentSerializerMixin, BaseSerializer):
            class Meta:
                model = WorkOrder
                fields = '__all__'
    
    This automatically adds file and image information to API responses
    """
    
    def add_file_info_to_response(self, instance, response):
        """Add file attachment information to the serializer response"""
        
        # Add image information
        response['image'] = None
        if hasattr(instance, 'image') and instance.image and not instance.image.is_deleted:
            response['image'] = {
                "id": str(instance.image.id),
                "url": instance.image.get_file_url(),
                "original_filename": instance.image.original_filename,
                "file_size": instance.image.file_size,
                "download_url": instance.image.get_download_url()
            }
        
        # Add files information
        if hasattr(instance, 'files'):
            files_count = instance.files.not_deleted().count()
            images_count = instance.files.not_deleted().images().count()
            
            # Generate model name for API endpoints
            app_label = instance._meta.app_label
            model_name = instance.__class__.__name__.lower()
            full_model_name = f"{app_label}.{model_name}"
            
            response['files'] = {
                "total_count": files_count,
                "images_count": images_count,
                "documents_count": instance.files.not_deleted().documents().count(),
                "files_endpoint": f"/v1/api/file-uploads/files/?link_to_model={full_model_name}&object_id={instance.id}",
                "upload_endpoint": "/v1/api/file-uploads/files/",
                "upload_example": {
                    "method": "POST",
                    "url": "/v1/api/file-uploads/files/",
                    "content_type": "multipart/form-data",
                    "data": {
                        "file": "<file_object>",
                        "link_to_model": full_model_name,
                        "link_to_id": str(instance.id),
                        "description": "Optional description",
                        "tags": "Optional,comma,separated,tags"
                    }
                }
            }
            
            # Add set-image endpoint if the model has an image field
            if hasattr(instance, 'image'):
                response['files']["set_image_endpoint"] = f"/v1/api/{app_label}/{model_name}/{instance.id}/set-image/"
        
        return response
    
    def to_representation(self, instance):
        """Override to automatically add file information"""
        response = super().to_representation(instance)
        
        # Add file information if the instance has file capabilities
        if hasattr(instance, 'files') or hasattr(instance, 'image'):
            response = self.add_file_info_to_response(instance, response)
        
        return response


class FileAttachmentViewMixin:
    """
    Mixin to add set-image functionality to views
    
    Usage:
        class WorkOrderBaseView(FileAttachmentViewMixin, BaseAPIView):
            # your existing view code
            pass
    
    This adds the set_image method for managing main images
    """
    
    def set_image(self, request, pk, *args, **kwargs):
        """
        Set the main image for an object from one of its uploaded files.
        Expects: {"file_id": "uuid-of-uploaded-file"} or {"file_id": null} to remove image
        """
        try:
            # Get the object instance
            instance = self.get_instance(pk)
            
            # Check if the model supports images
            if not hasattr(instance, 'image'):
                raise LocalBaseException(
                    exception="This model does not support image attachments",
                    status_code=400
                )
            
            # Get request data
            data = request.data
            file_id = data.get('file_id')
            
            if file_id is None:
                # Remove the current image
                instance.set_image(None)
                message = "Image removed successfully"
            else:
                # Get the file upload instance
                try:
                    from file_uploads.models import FileUpload
                    file_upload = FileUpload.objects.get(id=file_id, is_deleted=False)
                except FileUpload.DoesNotExist:
                    raise LocalBaseException(
                        exception="File not found or has been deleted",
                        status_code=404
                    )
                
                # Set the image (this will validate that the file belongs to the object)
                try:
                    instance.set_image(file_upload)
                    message = f"Image set to {file_upload.original_filename}"
                except ValueError as e:
                    raise LocalBaseException(
                        exception=str(e),
                        status_code=400
                    )
            
            # Return updated object data
            response_data = self.serializer_class(instance).data
            response_data['message'] = message
            
            return self.format_response(data=response_data, status_code=200)
            
        except Exception as e:
            return self.handle_exception(e)