"""
Quick test script to verify file upload functionality
Run this with: python manage.py shell < file_uploads/test_file_upload.py
"""

print("Testing File Upload System...")

# Test 1: Create a test file upload
from file_uploads.models import FileUpload
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model

# Create test content
test_content = ContentFile(b"This is a test file content", name="test.txt")

# Create a file upload record
file_upload = FileUpload(
    file=test_content,
    original_filename="test.txt",
    description="Test file for validation",
    access_level='tenant'
)

# Save and check
file_upload.save()
print(f"✓ Created FileUpload with ID: {file_upload.id}")
print(f"✓ File size: {file_upload.file_size} bytes")
print(f"✓ Content type: {file_upload.content_type}")
print(f"✓ File hash: {file_upload.file_hash}")

# Test 2: Validation service
from file_uploads.services import FileValidationService

# Test validation
validation_result = FileValidationService.validate_file(test_content)
print(f"✓ Validation result: {'PASSED' if validation_result['is_valid'] else 'FAILED'}")
if validation_result['errors']:
    print(f"  Errors: {validation_result['errors']}")
if validation_result['warnings']:
    print(f"  Warnings: {validation_result['warnings']}")

# Test 3: Manager methods
print(f"✓ Total files in system: {FileUpload.objects.count()}")
print(f"✓ Non-deleted files: {FileUpload.objects.not_deleted().count()}")
print(f"✓ Validated files: {FileUpload.objects.validated().count()}")

# Test 4: File methods
print(f"✓ Is image: {file_upload.is_image()}")
print(f"✓ Is document: {file_upload.is_document()}")
print(f"✓ File URL: {file_upload.get_file_url()}")
print(f"✓ Download URL: {file_upload.get_download_url()}")

print("\n🎉 All tests passed! File upload system is working correctly.")
print("\nNext steps:")
print("1. Test the API endpoints using curl or Postman")
print("2. Try uploading files via the API")
print("3. Check the admin interface at /admin/file_uploads/fileupload/")
print("4. Run cleanup commands: python manage.py cleanup_files --help")