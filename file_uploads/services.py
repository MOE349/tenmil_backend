"""
File upload validation and management services
"""
import os
import hashlib
import magic
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile


class FileValidationService:
    """
    Service for validating uploaded files for security and compliance
    """
    
    # File size limits (in bytes)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB for images
    
    # Allowed file extensions and their corresponding MIME types
    ALLOWED_EXTENSIONS = {
        # Documents
        '.pdf': ['application/pdf'],
        '.doc': ['application/msword'],
        '.docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
        '.xls': ['application/vnd.ms-excel'],
        '.xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
        '.ppt': ['application/vnd.ms-powerpoint'],
        '.pptx': ['application/vnd.openxmlformats-officedocument.presentationml.presentation'],
        '.txt': ['text/plain'],
        '.csv': ['text/csv', 'application/csv'],
        '.rtf': ['application/rtf', 'text/rtf'],
        
        # Images
        '.jpg': ['image/jpeg'],
        '.jpeg': ['image/jpeg'],
        '.png': ['image/png'],
        '.gif': ['image/gif'],
        '.webp': ['image/webp'],
        '.svg': ['image/svg+xml'],
        '.bmp': ['image/bmp'],
        '.tiff': ['image/tiff'],
        '.ico': ['image/x-icon'],
        
        # Videos
        '.mp4': ['video/mp4'],
        '.avi': ['video/x-msvideo'],
        '.mov': ['video/quicktime'],
        '.wmv': ['video/x-ms-wmv'],
        '.flv': ['video/x-flv'],
        '.webm': ['video/webm'],
        
        # Audio
        '.mp3': ['audio/mpeg'],
        '.wav': ['audio/wav'],
        '.ogg': ['audio/ogg'],
        '.m4a': ['audio/mp4'],
        
        # Archives
        '.zip': ['application/zip'],
        '.rar': ['application/x-rar-compressed'],
        '.7z': ['application/x-7z-compressed'],
        '.tar': ['application/x-tar'],
        '.gz': ['application/gzip'],
    }
    
    # Dangerous file extensions to always reject
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.scr', '.pif', '.msi', '.dll',
        '.vbs', '.js', '.jar', '.app', '.deb', '.rpm', '.dmg',
        '.php', '.asp', '.aspx', '.jsp', '.pl', '.py', '.rb', '.sh'
    }
    
    @classmethod
    def validate_file(cls, uploaded_file: UploadedFile) -> dict:
        """
        Comprehensive file validation
        
        Args:
            uploaded_file: Django UploadedFile instance
            
        Returns:
            dict: Validation result with status and any errors
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'file_info': {
                'original_name': uploaded_file.name,
                'size': uploaded_file.size,
                'content_type': uploaded_file.content_type,
            }
        }
        
        try:
            # 1. Basic file checks
            cls._validate_file_basics(uploaded_file, result)
            
            # 2. Extension validation
            cls._validate_file_extension(uploaded_file, result)
            
            # 3. Size validation
            cls._validate_file_size(uploaded_file, result)
            
            # 4. MIME type validation
            cls._validate_mime_type(uploaded_file, result)
            
            # 5. Content validation (if magic library is available)
            try:
                cls._validate_file_content(uploaded_file, result)
            except ImportError:
                result['warnings'].append('Advanced content validation unavailable')
            
            # 6. Security checks
            cls._validate_file_security(uploaded_file, result)
            
        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f'Validation error: {str(e)}')
        
        return result
    
    @classmethod
    def _validate_file_basics(cls, uploaded_file: UploadedFile, result: dict):
        """Basic file validation"""
        if not uploaded_file:
            result['is_valid'] = False
            result['errors'].append('No file provided')
            return
        
        if not uploaded_file.name:
            result['is_valid'] = False
            result['errors'].append('File has no name')
            return
        
        if uploaded_file.size == 0:
            result['is_valid'] = False
            result['errors'].append('File is empty')
            return
    
    @classmethod
    def _validate_file_extension(cls, uploaded_file: UploadedFile, result: dict):
        """Validate file extension"""
        name = uploaded_file.name.lower()
        ext = os.path.splitext(name)[1]
        
        if not ext:
            result['is_valid'] = False
            result['errors'].append('File has no extension')
            return
        
        # Check for dangerous extensions
        if ext in cls.DANGEROUS_EXTENSIONS:
            result['is_valid'] = False
            result['errors'].append(f'File type {ext} is not allowed for security reasons')
            return
        
        # Check if extension is in allowed list
        if ext not in cls.ALLOWED_EXTENSIONS:
            result['is_valid'] = False
            result['errors'].append(f'File type {ext} is not supported')
            return
        
        result['file_info']['extension'] = ext
    
    @classmethod
    def _validate_file_size(cls, uploaded_file: UploadedFile, result: dict):
        """Validate file size"""
        size = uploaded_file.size
        
        if size > cls.MAX_FILE_SIZE:
            result['is_valid'] = False
            result['errors'].append(f'File size ({cls._format_size(size)}) exceeds maximum allowed size ({cls._format_size(cls.MAX_FILE_SIZE)})')
            return
        
        # Additional check for images
        ext = result['file_info'].get('extension', '')
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.tiff']:
            if size > cls.MAX_IMAGE_SIZE:
                result['is_valid'] = False
                result['errors'].append(f'Image size ({cls._format_size(size)}) exceeds maximum allowed size for images ({cls._format_size(cls.MAX_IMAGE_SIZE)})')
    
    @classmethod
    def _validate_mime_type(cls, uploaded_file: UploadedFile, result: dict):
        """Validate MIME type"""
        content_type = uploaded_file.content_type
        ext = result['file_info'].get('extension', '')
        
        if not content_type:
            result['warnings'].append('No MIME type provided')
            return
        
        # Check if MIME type matches extension
        allowed_types = cls.ALLOWED_EXTENSIONS.get(ext, [])
        if allowed_types and content_type not in allowed_types:
            result['warnings'].append(f'MIME type {content_type} does not match extension {ext}')
    
    @classmethod
    def _validate_file_content(cls, uploaded_file: UploadedFile, result: dict):
        """Validate file content using python-magic"""
        # This requires python-magic library
        # Install with: pip install python-magic
        
        try:
            # Read first chunk for content detection
            uploaded_file.seek(0)
            chunk = uploaded_file.read(8192)
            uploaded_file.seek(0)
            
            # Detect actual file type
            detected_type = magic.from_buffer(chunk, mime=True)
            result['file_info']['detected_mime_type'] = detected_type
            
            # Compare with declared type
            declared_type = uploaded_file.content_type
            if declared_type and detected_type != declared_type:
                result['warnings'].append(f'Detected MIME type ({detected_type}) differs from declared type ({declared_type})')
                
        except Exception as e:
            result['warnings'].append(f'Content validation failed: {str(e)}')
    
    @classmethod
    def _validate_file_security(cls, uploaded_file: UploadedFile, result: dict):
        """Security-focused validation"""
        name = uploaded_file.name.lower()
        
        # Check for suspicious file names
        suspicious_patterns = [
            'script', 'iframe', 'object', 'embed', 'form',
            'javascript:', 'vbscript:', 'data:', 'file:',
            '<', '>', '"', "'", '&', '%', ';'
        ]
        
        for pattern in suspicious_patterns:
            if pattern in name:
                result['warnings'].append(f'Suspicious pattern "{pattern}" found in filename')
        
        # Check for double extensions
        parts = name.split('.')
        if len(parts) > 2:
            # Check if any part before the last one is a dangerous extension
            for i in range(len(parts) - 1):
                if f'.{parts[i]}' in cls.DANGEROUS_EXTENSIONS:
                    result['is_valid'] = False
                    result['errors'].append('File appears to have double extension with dangerous type')
                    break
        
        # File name length check
        if len(name) > 255:
            result['is_valid'] = False
            result['errors'].append('Filename is too long')
    
    @staticmethod
    def _format_size(size_bytes):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    @classmethod
    def generate_secure_filename(cls, original_filename: str) -> str:
        """
        Generate a secure filename from the original filename
        """
        import uuid
        import re
        
        # Extract extension
        name, ext = os.path.splitext(original_filename)
        ext = ext.lower()
        
        # Sanitize the filename
        name = re.sub(r'[^a-zA-Z0-9_-]', '', name)
        name = name[:50]  # Limit length
        
        # Generate UUID-based filename
        secure_name = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        
        return secure_name


class FileCleanupService:
    """
    Service for cleaning up orphaned and deleted files
    """
    
    @classmethod
    def find_orphaned_files(cls):
        """
        Find files that exist on disk but not in database
        """
        from file_uploads.models import FileUpload
        import glob
        
        # Get all files from database
        db_files = set()
        for file_obj in FileUpload.objects.all():
            if file_obj.file:
                db_files.add(file_obj.file.path)
        
        # Get all files from disk
        media_root = settings.MEDIA_ROOT
        upload_pattern = os.path.join(media_root, 'uploads', '**', '*')
        disk_files = set(glob.glob(upload_pattern, recursive=True))
        
        # Remove directories from disk_files
        disk_files = {f for f in disk_files if os.path.isfile(f)}
        
        # Find orphaned files
        orphaned = disk_files - db_files
        
        return list(orphaned)
    
    @classmethod
    def find_missing_files(cls):
        """
        Find database records that reference missing files
        """
        from file_uploads.models import FileUpload
        
        missing = []
        for file_obj in FileUpload.objects.filter(is_deleted=False):
            if file_obj.file and not os.path.exists(file_obj.file.path):
                missing.append(file_obj)
        
        return missing
    
    @classmethod
    def cleanup_soft_deleted_files(cls, days_old=7):
        """
        Remove files that have been soft-deleted for more than specified days
        """
        from file_uploads.models import FileUpload
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days_old)
        
        old_deleted_files = FileUpload.objects.filter(
            is_deleted=True,
            deleted_at__lt=cutoff_date
        )
        
        cleaned_count = 0
        for file_obj in old_deleted_files:
            try:
                file_obj.delete(hard_delete=True)
                cleaned_count += 1
            except Exception as e:
                print(f"Error cleaning up file {file_obj.id}: {e}")
        
        return cleaned_count