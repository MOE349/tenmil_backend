import os
from django.http import HttpResponse
from django.contrib.contenttypes.models import ContentType
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
                # Handle downloads with special authentication handling
                return self.download_with_auth_handling(request, kwargs.get('pk'))
            elif action == 'serve' and request.method == 'GET':
                # Handle serve with special authentication handling
                return self.serve_with_auth_handling(request, kwargs.get('pk'))
            elif action == 'hard_delete' and request.method == 'POST':
                return self.hard_delete(request, kwargs.get('pk'))
            elif action == 'stats' and request.method == 'GET':
                return self.stats(request)
        
        return super().dispatch(request, *args, **kwargs)
    
    def download_with_auth_handling(self, request, pk):
        """Handle download with flexible authentication"""
        try:
            # Get the file directly without going through BaseAPIView authentication
            instance = FileUpload.objects.get_object_or_404(raise_exception=True, id=pk)
            
            # Get user (might be None for unauthenticated requests)
            user = getattr(request, 'user', None)
            
            # Check if we can access this file
            if not self._can_access_file(instance, user):
                raise LocalBaseException(exception="You don't have permission to access this file", status_code=403)
            
            # If we reach here, we can download the file
            return self.download_file(request, instance)
            
        except LocalBaseException:
            # Re-raise permission/not found errors
            raise
        except Exception as e:
            # Handle other errors (like authentication errors) gracefully
            raise LocalBaseException(exception=f"Error accessing file: {str(e)}", status_code=500)
    
    def serve_with_auth_handling(self, request, pk):
        """Handle serve with flexible authentication"""
        try:
            # Get the file directly without going through BaseAPIView authentication
            instance = FileUpload.objects.get_object_or_404(raise_exception=True, id=pk)
            
            # Get user (might be None for unauthenticated requests)
            user = getattr(request, 'user', None)
            
            # Check if we can access this file
            if not self._can_access_file(instance, user):
                raise LocalBaseException(exception="You don't have permission to access this file", status_code=403)
            
            # If we reach here, we can serve the file
            return self.serve_file(request, instance)
            
        except LocalBaseException:
            # Re-raise permission/not found errors
            raise
        except Exception as e:
            # Handle other errors (like authentication errors) gracefully
            raise LocalBaseException(exception=f"Error accessing file: {str(e)}", status_code=500)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if hasattr(self, 'request') and self.request.method == 'POST':
            return FileUploadCreateSerializer
        elif hasattr(self, 'request') and self.request.method == 'GET' and not getattr(self, 'kwargs', {}).get('pk'):
            return FileUploadListSerializer
        return FileUploadSerializer
    
    def get_request_params(self, request):
        """Override to handle custom file upload parameters"""
        params = super().get_request_params(request)
        
        # Handle link_to_model parameter (BaseAPIView adds __icontains automatically)
        link_to_model_key = None
        model_name = None
        
        # Check for various forms of the parameter
        for key in ['link_to_model', 'link_to_model__icontains']:
            if key in params:
                link_to_model_key = key
                model_name = params.pop(key)
                break
        
        if model_name:
            # Handle case where model_name might be a list
            if isinstance(model_name, list):
                model_name = model_name[0] if model_name else ""
            
            try:
                if isinstance(model_name, str) and '.' in model_name:
                    # Convert model name to content_type_ref
                    app_label, model = model_name.split('.')
                    content_type = ContentType.objects.get(app_label=app_label, model=model)
                    params['content_type_ref'] = content_type.id
            except (ValueError, ContentType.DoesNotExist, AttributeError):
                # Invalid model reference, ignore it
                pass
        
        return params
    
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
            
            # Handle case where model_name might be a list (from form data)
            if isinstance(model_name, list):
                model_name = model_name[0] if model_name else ""
            
            # Handle case where object_id might be a list
            if isinstance(object_id, list):
                object_id = object_id[0] if object_id else ""
            
            try:
                # Validate model_name format
                if isinstance(model_name, str) and '.' in model_name:
                    # Get content type from model name
                    app_label, model = model_name.split('.')
                    content_type = ContentType.objects.get(app_label=app_label, model=model)
                    data['content_type_ref'] = content_type.id
                    data['object_id'] = object_id
            except (ValueError, ContentType.DoesNotExist, AttributeError):
                # Invalid model reference, let validation handle it
                pass
        
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
                status_code=201
            )
        except Exception as e:
            # Clean up file if creation failed
            if 'file' in data and hasattr(data['file'], 'temporary_file_path'):
                try:
                    os.remove(data['file'].temporary_file_path())
                except:
                    pass
            return self.handle_exception(e)
    
    def destroy(self, request, pk, *args, **kwargs):
        """Override to soft delete files"""
        try:
            instance = self.get_instance(pk)
            
            # Check if user has permission to delete
            user = request.user
            if not user or (instance.uploaded_by != user and not user.is_staff):
                raise LocalBaseException(exception="You don't have permission to delete this file", status_code=403)
            
            # Soft delete
            instance.delete(hard_delete=False)
            
            return self.format_response(
                data={}, 
                status_code=204
            )
        except Exception as e:
            return self.handle_exception(e)
    
    def hard_delete(self, request, pk=None):
        """Hard delete a file (admin only)"""
        try:
            user = request.user
            if not user or not user.is_staff:
                raise LocalBaseException(exception="Only staff can permanently delete files", status_code=403)
            
            instance = self.get_instance(pk)
            instance.delete(hard_delete=True)
            
            return self.format_response(
                data={}, 
                status_code=204
            )
        except Exception as e:
            return self.handle_exception(e)
    
    def download(self, request, pk=None):
        """Download a file with proper headers (legacy method)"""
        try:
            instance = self.get_instance(pk)
            return self.download_file(request, instance)
        except Exception as e:
            raise LocalBaseException(exception=f"Error downloading file: {str(e)}", status_code=500)
    
    def download_file(self, request, instance):
        """Download a file with proper headers (permissions already checked)"""
        try:
            # Check if file exists
            if not instance.file or not os.path.exists(instance.file.path):
                raise LocalBaseException(exception="File not found", status_code=404)
            
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
                
        except LocalBaseException:
            # Re-raise LocalBaseException to be handled by the exception handler
            raise
        except Exception as e:
            # Wrap other exceptions in LocalBaseException
            raise LocalBaseException(exception=f"Error downloading file: {str(e)}", status_code=500)
    
    def serve(self, request, pk=None):
        """Serve a file inline (for images, PDFs, etc.) (legacy method)"""
        try:
            instance = self.get_instance(pk)
            return self.serve_file(request, instance)
        except Exception as e:
            raise LocalBaseException(exception=f"Error serving file: {str(e)}", status_code=500)
    
    def serve_file(self, request, instance):
        """Serve a file inline (permissions already checked)"""
        try:
            # Check if file exists
            if not instance.file or not os.path.exists(instance.file.path):
                raise LocalBaseException(exception="File not found", status_code=404)
            
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
                
        except LocalBaseException:
            # Re-raise LocalBaseException to be handled by the exception handler
            raise
        except Exception as e:
            # Wrap other exceptions in LocalBaseException
            raise LocalBaseException(exception=f"Error serving file: {str(e)}", status_code=500)
    
    def stats(self, request):
        """Get file upload statistics"""
        try:
            user = request.user if hasattr(request, 'user') else None
            if not user:
                raise LocalBaseException(exception="Authentication required", status_code=401)
            
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
        # Debug information (only in development)
        from django.conf import settings
        if settings.DEBUG:
            print(f"[DEBUG] File access check:")
            print(f"  - File ID: {file_obj.id}")
            print(f"  - Access level: {file_obj.access_level}")
            print(f"  - Uploaded by: {file_obj.uploaded_by}")
            print(f"  - Current user: {user}")
            print(f"  - User authenticated: {user.is_authenticated if user else False}")
            print(f"  - User is staff: {user.is_staff if user else False}")
        
        # TEMPORARY DEBUGGING: Allow all access to see what's happening
        # TODO: Remove this and implement proper permissions
        if settings.DEBUG:
            print(f"[DEBUG] TEMPORARY: Allowing all file access for debugging")
            return True
        
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