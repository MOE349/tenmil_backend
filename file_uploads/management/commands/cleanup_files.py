"""
Management command for cleaning up orphaned and deleted files
"""
import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from file_uploads.services import FileCleanupService
from file_uploads.models import FileUpload


class Command(BaseCommand):
    help = 'Clean up orphaned files and soft-deleted files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--orphaned',
            action='store_true',
            help='Clean up orphaned files (files on disk but not in database)',
        )
        parser.add_argument(
            '--soft-deleted',
            action='store_true',
            help='Clean up soft-deleted files',
        )
        parser.add_argument(
            '--missing',
            action='store_true',
            help='Report missing files (database records without files)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='For soft-deleted cleanup: minimum age in days (default: 7)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompts',
        )

    def handle(self, *args, **options):
        if not any([options['orphaned'], options['soft_deleted'], options['missing']]):
            self.stdout.write(
                self.style.WARNING(
                    'Please specify at least one action: --orphaned, --soft-deleted, or --missing'
                )
            )
            return

        # Check for missing files
        if options['missing']:
            self.handle_missing_files(options)

        # Clean up orphaned files
        if options['orphaned']:
            self.handle_orphaned_files(options)

        # Clean up soft-deleted files
        if options['soft_deleted']:
            self.handle_soft_deleted_files(options)

    def handle_missing_files(self, options):
        """Handle missing files reporting"""
        self.stdout.write("Checking for missing files...")
        
        missing_files = FileCleanupService.find_missing_files()
        
        if not missing_files:
            self.stdout.write(self.style.SUCCESS("No missing files found."))
            return

        self.stdout.write(
            self.style.WARNING(f"Found {len(missing_files)} database records with missing files:")
        )
        
        for file_obj in missing_files:
            self.stdout.write(f"  - ID: {file_obj.id}, Original: {file_obj.original_filename}")
            self.stdout.write(f"    Expected path: {file_obj.file.path if file_obj.file else 'No path'}")
        
        if not options['dry_run']:
            if options['force'] or self._confirm("Mark these records as deleted?"):
                for file_obj in missing_files:
                    file_obj.is_deleted = True
                    file_obj.save()
                self.stdout.write(
                    self.style.SUCCESS(f"Marked {len(missing_files)} records as deleted.")
                )

    def handle_orphaned_files(self, options):
        """Handle orphaned files cleanup"""
        self.stdout.write("Scanning for orphaned files...")
        
        orphaned_files = FileCleanupService.find_orphaned_files()
        
        if not orphaned_files:
            self.stdout.write(self.style.SUCCESS("No orphaned files found."))
            return

        total_size = sum(os.path.getsize(f) for f in orphaned_files if os.path.exists(f))
        
        self.stdout.write(
            self.style.WARNING(
                f"Found {len(orphaned_files)} orphaned files "
                f"({self._format_size(total_size)}):"
            )
        )
        
        for file_path in orphaned_files[:10]:  # Show first 10
            size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            self.stdout.write(f"  - {file_path} ({self._format_size(size)})")
        
        if len(orphaned_files) > 10:
            self.stdout.write(f"  ... and {len(orphaned_files) - 10} more files")

        if not options['dry_run']:
            if options['force'] or self._confirm("Delete these orphaned files?"):
                deleted_count = 0
                for file_path in orphaned_files:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            deleted_count += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Failed to delete {file_path}: {e}")
                        )
                
                self.stdout.write(
                    self.style.SUCCESS(f"Deleted {deleted_count} orphaned files.")
                )

    def handle_soft_deleted_files(self, options):
        """Handle soft-deleted files cleanup"""
        days = options['days']
        self.stdout.write(f"Cleaning up files soft-deleted more than {days} days ago...")
        
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        old_deleted_files = FileUpload.objects.filter(
            is_deleted=True,
            deleted_at__lt=cutoff_date
        )
        
        count = old_deleted_files.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No old soft-deleted files found."))
            return

        total_size = sum(
            f.file_size for f in old_deleted_files 
            if f.file_size
        )

        self.stdout.write(
            self.style.WARNING(
                f"Found {count} soft-deleted files older than {days} days "
                f"({self._format_size(total_size)}):"
            )
        )
        
        # Show sample files
        sample_files = old_deleted_files[:5]
        for file_obj in sample_files:
            self.stdout.write(
                f"  - {file_obj.original_filename} "
                f"(deleted: {file_obj.deleted_at.strftime('%Y-%m-%d')})"
            )
        
        if count > 5:
            self.stdout.write(f"  ... and {count - 5} more files")

        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS(f"DRY RUN: Would permanently delete {count} files.")
            )
            return

        if options['force'] or self._confirm("Permanently delete these files?"):
            cleaned_count = FileCleanupService.cleanup_soft_deleted_files(days)
            self.stdout.write(
                self.style.SUCCESS(f"Permanently deleted {cleaned_count} files.")
            )

    def _confirm(self, message):
        """Ask for user confirmation"""
        response = input(f"{message} [y/N]: ")
        return response.lower() in ['y', 'yes']

    def _format_size(self, size_bytes):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"