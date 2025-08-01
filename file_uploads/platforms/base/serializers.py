from rest_framework import serializers
from configurations.base_features.serializers.base_serializer import BaseSerializer
from file_uploads.models import FileUpload


class FileUploadSerializer(BaseSerializer):
    """
    Base serializer for FileUpload model
    """
    file_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    is_image = serializers.SerializerMethodField()
    is_document = serializers.SerializerMethodField()
    file_size_human = serializers.SerializerMethodField()
    
    class Meta:
        model = FileUpload
        fields = [
            'id', 'file', 'original_filename', 'file_size', 'file_size_human',
            'content_type', 'file_hash', 'description', 'tags',
            'is_validated', 'validation_status', 'validation_errors',
            'uploaded_by', 'is_public', 'access_level',
            'content_type_ref', 'object_id', 'content_object',
            'is_deleted', 'deleted_at', 'created_at', 'updated_at',
            'file_url', 'download_url', 'is_image', 'is_document'
        ]
        read_only_fields = [
            'id', 'file_size', 'content_type', 'file_hash', 
            'is_validated', 'validation_status', 'validation_errors',
            'is_deleted', 'deleted_at', 'created_at', 'updated_at',
            'file_url', 'download_url', 'is_image', 'is_document', 'file_size_human'
        ]
    
    def get_file_url(self, obj):
        """Get the file URL"""
        return obj.get_file_url()
    
    def get_download_url(self, obj):
        """Get the download URL"""
        return obj.get_download_url()
    
    def get_is_image(self, obj):
        """Check if file is an image"""
        return obj.is_image()
    
    def get_is_document(self, obj):
        """Check if file is a document"""
        return obj.is_document()
    
    def get_file_size_human(self, obj):
        """Convert file size to human readable format"""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    def mod_create(self, validated_data):
        """Override to set user from request"""
        request = self.get_request()
        if request and hasattr(request, 'user'):
            validated_data['uploaded_by'] = request.user
        
        # Create the instance
        instance = super().mod_create(validated_data)
        
        # Generate file hash after creation
        if instance.file:
            instance.generate_file_hash()
            instance.save()
        
        return instance
    
    def mod_to_representation(self, instance):
        """Override to filter sensitive data based on access level"""
        representation = super().mod_to_representation(instance)
        
        request = self.get_request()
        user = self.get_user()
        
        # Handle content_object properly to avoid JSON serialization errors
        if 'content_object' in representation and instance.content_object:
            # Instead of including the full object, provide basic info
            content_obj = instance.content_object
            representation['content_object'] = {
                'model': f"{content_obj._meta.app_label}.{content_obj._meta.model_name}",
                'id': str(content_obj.id),
                'name': getattr(content_obj, 'name', None) or getattr(content_obj, 'title', None) or str(content_obj)
            }
        elif 'content_object' in representation:
            representation['content_object'] = None
        
        # Hide sensitive fields for non-owners
        if user and instance.uploaded_by != user:
            if instance.access_level == 'private':
                # For private files, only show basic info to non-owners
                allowed_fields = ['id', 'original_filename', 'file_size_human', 'content_type']
                representation = {k: v for k, v in representation.items() if k in allowed_fields}
        
        return representation


class FileUploadCreateSerializer(BaseSerializer):
    """
    Serializer for creating file uploads with validation
    """
    # Additional fields for easier API usage (these are converted in the view)
    link_to_model = serializers.CharField(required=False, write_only=True, help_text="Model to link to (e.g., 'assets.equipment')")
    link_to_id = serializers.CharField(required=False, write_only=True, help_text="ID of the object to link to")
    
    class Meta:
        model = FileUpload
        fields = [
            'file', 'description', 'tags', 'is_public', 'access_level',
            'content_type_ref', 'object_id', 'link_to_model', 'link_to_id'
        ]
    
    def validate_file(self, value):
        """Validate file upload"""
        # Check file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        if value.size > max_size:
            raise serializers.ValidationError("File size cannot exceed 50MB")
        
        # Check file extension
        import os
        ext = os.path.splitext(value.name)[1].lower()
        allowed_extensions = [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.txt', '.csv', '.jpg', '.jpeg', '.png', '.gif', '.svg',
            '.mp4', '.avi', '.mov', '.zip', '.rar', '.7z'
        ]
        
        if ext not in allowed_extensions:
            raise serializers.ValidationError(f"File type {ext} is not allowed")
        
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        link_to_model = attrs.get('link_to_model')
        link_to_id = attrs.get('link_to_id')
        
        # If linking to a model, both fields are required
        if link_to_model or link_to_id:
            if not (link_to_model and link_to_id):
                raise serializers.ValidationError(
                    "Both 'link_to_model' and 'link_to_id' are required when linking to an object"
                )
            
            # Validate model format
            if '.' not in link_to_model:
                raise serializers.ValidationError(
                    "'link_to_model' must be in format 'app_label.model_name' (e.g., 'assets.equipment')"
                )
        
        return attrs
    
    def mod_create(self, validated_data):
        """Override to set metadata and validate"""
        request = self.get_request()
        if request and hasattr(request, 'user'):
            validated_data['uploaded_by'] = request.user
        
        # Set original filename
        if 'file' in validated_data and validated_data['file']:
            validated_data['original_filename'] = validated_data['file'].name
        
        # Create instance
        instance = super().mod_create(validated_data)
        
        # Generate hash and run validation
        if instance.file:
            instance.generate_file_hash()
            # Mark as validated for now (in production, this would trigger async validation)
            instance.is_validated = True
            instance.validation_status = 'passed'
            instance.save()
        
        return instance


class FileUploadListSerializer(BaseSerializer):
    """
    Simplified serializer for listing files
    """
    file_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    file_size_human = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = FileUpload
        fields = [
            'id', 'original_filename', 'file_size_human', 'content_type',
            'description', 'tags', 'validation_status', 'is_public',
            'access_level', 'uploaded_by_name', 'created_at',
            'file_url', 'download_url'
        ]
    
    def get_file_url(self, obj):
        return obj.get_file_url()
    
    def get_download_url(self, obj):
        return obj.get_download_url()
    
    def get_file_size_human(self, obj):
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return getattr(obj.uploaded_by, 'username', str(obj.uploaded_by))
        return None