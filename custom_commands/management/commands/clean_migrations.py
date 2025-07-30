import os
import glob
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Remove all migration files while keeping migrations folders and __init__.py files"

    def add_arguments(self, parser):
        parser.add_argument(
            '--app',
            type=str,
            help='Specific app name to clean migrations for (if not provided, cleans all apps)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting files'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force deletion without confirmation prompt'
        )

    def handle(self, *args, **options):
        app_name = options.get('app')
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)
        
        # Get all Django apps in the project
        if app_name:
            apps_to_clean = [app_name]
        else:
            apps_to_clean = self.get_all_django_apps()
        
        if not apps_to_clean:
            self.stdout.write(
                self.style.WARNING('No Django apps found to clean.')
            )
            return
        
        # Collect files to be removed
        files_to_remove = []
        for app in apps_to_clean:
            migration_files = self.get_migration_files(app)
            files_to_remove.extend(migration_files)
        
        if not files_to_remove:
            self.stdout.write(
                self.style.SUCCESS('No migration files found to remove.')
            )
            return
        
        # Display files that will be removed
        self.stdout.write(
            self.style.WARNING(f'Found {len(files_to_remove)} migration files to remove:')
        )
        for file_path in files_to_remove:
            self.stdout.write(f'  - {file_path}')
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS('\nDry run completed. No files were actually removed.')
            )
            return
        
        # Confirmation prompt (unless --force is used)
        if not force:
            confirm = input('\nAre you sure you want to remove these files? (y/N): ')
            if confirm.lower() not in ['y', 'yes']:
                self.stdout.write(
                    self.style.WARNING('Operation cancelled.')
                )
                return
        
        # Remove the files
        removed_count = 0
        for file_path in files_to_remove:
            try:
                os.remove(file_path)
                removed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Removed: {file_path}')
                )
            except OSError as e:
                self.stdout.write(
                    self.style.ERROR(f'Error removing {file_path}: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully removed {removed_count} migration files.')
        )
    
    def get_all_django_apps(self):
        """Get list of all Django apps in the project by looking for directories with migrations folders."""
        apps = []
        project_root = os.getcwd()
        
        # Look for directories that contain migrations folders
        for item in os.listdir(project_root):
            item_path = os.path.join(project_root, item)
            if (os.path.isdir(item_path) and 
                not item.startswith('.') and 
                not item.startswith('__') and
                item not in ['static', 'staticfiles', 'media', 'deployment', 'docker', 'configurations']):
                
                migrations_path = os.path.join(item_path, 'migrations')
                if os.path.exists(migrations_path) and os.path.isdir(migrations_path):
                    apps.append(item)
        
        return apps
    
    def get_migration_files(self, app_name):
        """Get list of migration files for a specific app (excluding __init__.py)."""
        migrations_dir = os.path.join(os.getcwd(), app_name, 'migrations')
        
        if not os.path.exists(migrations_dir):
            self.stdout.write(
                self.style.WARNING(f'Migrations directory not found for app: {app_name}')
            )
            return []
        
        # Find all .py files in migrations directory except __init__.py
        migration_files = []
        for file_path in glob.glob(os.path.join(migrations_dir, '*.py')):
            if not file_path.endswith('__init__.py'):
                migration_files.append(file_path)
        
        return migration_files