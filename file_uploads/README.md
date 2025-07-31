# File Uploads App

A centralized file upload handler for the Tenmil platform, providing secure file management with comprehensive validation, access control, and lifecycle management.

## Features

### Core Functionality
- **Centralized File Storage**: Single point for all file operations across the platform
- **Generic Foreign Key Support**: Files can be linked to any model in the system
- **Multiple Access Levels**: Private, tenant-level, and public file access
- **Soft Delete**: Files are soft-deleted by default with cleanup management
- **File Validation**: Comprehensive security and content validation
- **Metadata Management**: Rich metadata including tags, descriptions, and file hashes

### Security Features
- **File Type Validation**: Whitelist of allowed file extensions and MIME types
- **Content Validation**: Deep content inspection using python-magic (optional)
- **Size Limits**: Configurable limits for different file types
- **Dangerous File Detection**: Automatic blocking of executable and script files
- **Hash Generation**: SHA-256 hashing for file integrity verification

### API Endpoints

All endpoints are available under `/v1/api/file-uploads/`

#### File Management
- `GET /files/` - List files (with filtering and pagination)
- `POST /files/` - Upload a new file
- `GET /files/{id}/` - Get file details
- `PATCH /files/{id}/` - Update file metadata
- `DELETE /files/{id}/` - Soft delete a file
- `POST /files/{id}/hard_delete/` - Permanently delete a file (admin only)

#### File Access
- `GET /files/{id}/download/` - Download file with attachment headers
- `GET /files/{id}/serve/` - Serve file inline (for images, PDFs)
- `GET /stats/` - Get user's file upload statistics

## Usage Examples

### Basic File Upload

```python
# Via API (multipart/form-data)
POST /v1/api/file-uploads/files/
Content-Type: multipart/form-data

{
    "file": <file_object>,
    "description": "Project documentation",
    "tags": "documentation,project,pdf",
    "access_level": "tenant",
    "is_public": false
}
```

### Linking Files to Models

```python
# Upload and link to an asset
POST /v1/api/file-uploads/files/
{
    "file": <file_object>,
    "link_to_model": "assets.equipment",
    "link_to_id": "asset-uuid-here",
    "description": "Equipment manual"
}
```

### Using in Other Models

```python
from django.contrib.contenttypes.fields import GenericRelation
from file_uploads.models import FileUpload

class Equipment(BaseModel):
    name = models.CharField(max_length=255)
    
    # Add generic relation to files
    files = GenericRelation(
        FileUpload,
        content_type_field='content_type_ref',
        object_id_field='object_id',
        related_query_name='equipment'
    )

# Usage
equipment = Equipment.objects.get(id=some_id)
files = equipment.files.all()  # Get all files for this equipment
```

### Programmatic File Creation

```python
from file_uploads.models import FileUpload
from django.core.files.base import ContentFile

# Create file programmatically
file_content = ContentFile(b"file content here", name="document.pdf")
file_upload = FileUpload.objects.create(
    file=file_content,
    original_filename="document.pdf",
    description="Generated report",
    uploaded_by=user,
    access_level='tenant'
)
```

## File Validation

The system includes comprehensive file validation:

### Allowed File Types
- **Documents**: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX, TXT, CSV, RTF
- **Images**: JPG, JPEG, PNG, GIF, WEBP, SVG, BMP, TIFF, ICO
- **Videos**: MP4, AVI, MOV, WMV, FLV, WEBM
- **Audio**: MP3, WAV, OGG, M4A
- **Archives**: ZIP, RAR, 7Z, TAR, GZ

### Size Limits
- General files: 50MB maximum
- Images: 10MB maximum

### Security Checks
- Dangerous file extension blocking
- Double extension detection
- Suspicious filename pattern detection
- MIME type verification
- Content inspection (with python-magic)

## Management Commands

### File Cleanup
```bash
# Clean up orphaned files (on disk but not in database)
python manage.py cleanup_files --orphaned

# Clean up soft-deleted files older than 7 days
python manage.py cleanup_files --soft-deleted --days 7

# Report missing files (in database but not on disk)
python manage.py cleanup_files --missing

# Dry run to see what would be cleaned
python manage.py cleanup_files --orphaned --dry-run

# Force cleanup without confirmation
python manage.py cleanup_files --orphaned --force
```

## Configuration

### Required Settings

```python
# Media files configuration (already added to settings)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Optional: Customize file validation
FILE_UPLOAD_MAX_SIZE = 50 * 1024 * 1024  # 50MB
FILE_UPLOAD_MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
```

### Optional Dependencies

For enhanced content validation:
```bash
pip install python-magic
```

## Models

### FileUpload
The main model with the following key fields:

- **Storage**: `file`, `original_filename`, `file_size`, `content_type`, `file_hash`
- **Metadata**: `description`, `tags`, `uploaded_by`
- **Validation**: `is_validated`, `validation_status`, `validation_errors`
- **Access Control**: `is_public`, `access_level`
- **Generic Relations**: `content_type_ref`, `object_id`, `content_object`
- **Lifecycle**: `is_deleted`, `deleted_at`, `created_at`, `updated_at`

## File Access Levels

1. **Private**: Only accessible by the file owner and staff
2. **Tenant**: Accessible by all authenticated users in the tenant
3. **Public**: Accessible by anyone (including anonymous users)

## Best Practices

1. **Always use the API**: Don't create FileUpload objects directly unless necessary
2. **Link files to models**: Use the generic foreign key to associate files with specific records
3. **Set appropriate access levels**: Consider data sensitivity when setting access levels
4. **Add descriptions and tags**: Helps with file organization and search
5. **Regular cleanup**: Run cleanup commands periodically to maintain disk space
6. **Monitor file usage**: Use the stats endpoint to track usage patterns

## Error Handling

The API returns structured error responses:

```json
{
    "success": false,
    "errors": ["File type .exe is not allowed for security reasons"],
    "data": null,
    "status_code": 400
}
```

## Admin Interface

The Django admin provides:
- File listing with filters and search
- File validation management
- Bulk operations (validate, delete, restore)
- File download links
- Soft delete management

Access via `/admin/file_uploads/fileupload/`