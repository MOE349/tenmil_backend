import os
import mimetypes
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.contrib.contenttypes.models import ContentType
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from configurations.base_features.views.base_api_view import BaseAPIView
from configurations.base_features.exceptions.base_exceptions import LocalBaseException
from file_uploads.models import FileUpload
from .serializers import (
    FileUploadSerializer, 
    FileUploadCreateSerializer, 
    FileUploadListSerializer
)


class FileUploadView(BaseAPIView):
    """
    Base view for file upload operations
    """
    model_class = FileUpload
    serializer_class = FileUploadSerializer
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to handle custom actions"""
        action = kwargs.get('action')
        if action:
            # Route to custom action methods
            if action == 'download' and request.method == 'GET':
                return self.download(request, kwargs.get('pk'))
            elif action == 'serve' and request.method == 'GET':
                return self.serve(request, kwargs.get('pk'))
            elif action == 'hard_delete' and request.method == 'POST':
                return self.hard_delete(request, kwargs.get('pk'))
            elif action == 'stats' and request.method == 'GET':
                return self.stats(request)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if hasattr(self, 'request') and self.request.method == 'POST':
            return FileUploadCreateSerializer
        elif hasattr(self, 'request') and self.request.method == 'GET' and not getattr(self, 'kwargs', {}).get('pk'):
            return FileUploadListSerializer
        return FileUploadSerializer
    
    def get_queryset(self, params=None, ordering=None):
        """Override to filter deleted files and apply access control"""
        queryset = super().get_queryset(params, ordering)
        
        # Filter out soft-deleted files
        queryset = queryset.filter(is_deleted=False)
        
        # Apply access control
        user = getattr(self, 'request', None)
        user = getattr(user, 'user', None) if user else None
        if user:
            # Users can see their own files, public files, and tenant-level files
            from django.db.models import Q
            queryset = queryset.filter(
                Q(uploaded_by=user) |
                Q(access_level='public') |
                Q(access_level='tenant')
            )
        else:
            # Anonymous users can only see public files
            queryset = queryset.filter(access_level='public')
        
        return queryset
    
    def handle_post_data(self, request):
        """Override to handle file upload specific data"""
        data = request.data.copy()
        
        # Handle generic foreign key setup if object linking is provided
        if 'link_to_model' in data and 'link_to_id' in data:
            model_name = data.pop('link_to_model')
            object_id = data.pop('link_to_id')
            
            try:
                # Get content type from model name
                app_label, model = model_name.split('.')
                content_type = ContentType.objects.get(app_label=app_label, model=model)
                data['content_type_ref'] = content_type.id
                data['object_id'] = object_id
            except (ValueError, ContentType.DoesNotExist):
                pass  # Invalid model reference, let validation handle it
        
        return data
    
    def create(self, data, params, *args, **kwargs):
        """Override to handle file upload creation"""
        serializer = self.get_serializer_class()(data=data, context={'request': self.request})
        serializer.is_valid(raise_exception=True)
        
        try:
            instance = serializer.save()
            response_serializer = FileUploadSerializer(instance, context={'request': self.request})
            return self.format_response(
                data=response_serializer.data, 
                status_code=201,
                message="File uploaded successfully"
            )
        except Exception as e:
            # Clean up file if creation failed
            if 'file' in data and hasattr(data['file'], 'temporary_file_path'):
                try:
                    os.remove(data['file'].temporary_file_path())
                except:
                    pass
            raise LocalBaseException(
                exception_type="file_upload_failed",
                status_code=400,
                exception=e
            )
    
    def destroy(self, request, pk, *args, **kwargs):
        """Override to soft delete files"""
        try:
            instance = self.get_instance(pk)
            
            # Check if user has permission to delete
            user = request.user
            if not user or (instance.uploaded_by != user and not user.is_staff):
                raise PermissionDenied("You don't have permission to delete this file")
            
            # Soft delete
            instance.delete(hard_delete=False)
            
            return self.format_response(
                data={}, 
                status_code=204,
                message="File deleted successfully"
            )
        except Exception as e:
            return self.handle_exception(e)
    
    def hard_delete(self, request, pk=None):
        """Hard delete a file (admin only)"""
        try:
            user = request.user
            if not user or not user.is_staff:
                raise PermissionDenied("Only staff can permanently delete files")
            
            instance = self.get_instance(pk)
            instance.delete(hard_delete=True)
            
            return self.format_response(
                data={}, 
                status_code=204,
                message="File permanently deleted"
            )
        except Exception as e:
            return self.handle_exception(e)
    
    def download(self, request, pk=None):
        """Download a file with proper headers"""
        try:
            instance = self.get_instance(pk)
            
            # Check access permissions
            user = request.user if hasattr(request, 'user') else None
            if not self._can_access_file(instance, user):
                raise PermissionDenied("You don't have permission to access this file")
            
            # Check if file exists
            if not instance.file or not os.path.exists(instance.file.path):
                raise Http404("File not found")
            
            # Prepare response
            file_path = instance.file.path
            content_type = instance.content_type or 'application/octet-stream'
            
            with open(file_path, 'rb') as file:
                response = HttpResponse(file.read(), content_type=content_type)
                response['Content-Disposition'] = f'attachment; filename="{instance.original_filename}"'
                response['Content-Length'] = instance.file_size
                
                # Add cache headers for images
                if instance.is_image():
                    response['Cache-Control'] = 'public, max-age=3600'
                
                return response
                
        except Exception as e:
            return self.handle_exception(e)
    
    def serve(self, request, pk=None):
        """Serve a file inline (for images, PDFs, etc.)"""
        try:
            instance = self.get_instance(pk)
            
            # Check access permissions
            user = request.user if hasattr(request, 'user') else None
            if not self._can_access_file(instance, user):
                raise PermissionDenied("You don't have permission to access this file")
            
            # Check if file exists
            if not instance.file or not os.path.exists(instance.file.path):
                raise Http404("File not found")
            
            # Prepare response
            file_path = instance.file.path
            content_type = instance.content_type or 'application/octet-stream'
            
            with open(file_path, 'rb') as file:
                response = HttpResponse(file.read(), content_type=content_type)
                response['Content-Disposition'] = f'inline; filename="{instance.original_filename}"'
                response['Content-Length'] = instance.file_size
                
                # Add cache headers
                response['Cache-Control'] = 'public, max-age=3600'
                
                return response
                
        except Exception as e:
            return self.handle_exception(e)
    
    def stats(self, request):
        """Get file upload statistics"""
        try:
            user = request.user if hasattr(request, 'user') else None
            if not user:
                raise PermissionDenied("Authentication required")
            
            queryset = self.get_queryset()
            user_files = queryset.filter(uploaded_by=user)
            
            stats = {
                'total_files': user_files.count(),
                'total_size': sum(f.file_size for f in user_files),
                'by_type': {},
                'by_status': {}
            }
            
            # Group by content type
            for file_obj in user_files:
                content_type = file_obj.content_type
                if content_type not in stats['by_type']:
                    stats['by_type'][content_type] = {'count': 0, 'size': 0}
                stats['by_type'][content_type]['count'] += 1
                stats['by_type'][content_type]['size'] += file_obj.file_size
            
            # Group by validation status
            for file_obj in user_files:
                status_val = file_obj.validation_status
                if status_val not in stats['by_status']:
                    stats['by_status'][status_val] = 0
                stats['by_status'][status_val] += 1
            
            return self.format_response(data=stats, status_code=200)
            
        except Exception as e:
            return self.handle_exception(e)
    
    def _can_access_file(self, file_obj, user):
        """Check if user can access the file"""
        # Public files are accessible to everyone
        if file_obj.access_level == 'public':
            return True
        
        # Anonymous users can't access non-public files
        if not user or not user.is_authenticated:
            return False
        
        # File owner can always access
        if file_obj.uploaded_by == user:
            return True
        
        # Staff can access everything
        if user.is_staff:
            return True
        
        # Tenant-level files are accessible to authenticated tenant users
        if file_obj.access_level == 'tenant':
            return True
        
        # Private files are only accessible to owner and staff
        return False