from django.core.management.base import BaseCommand
import os
import subprocess
import sys

class Command(BaseCommand):
    help = 'Start Celery beat scheduler for periodic tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--loglevel',
            type=str,
            default='INFO',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            help='Logging level'
        )

    def handle(self, *args, **options):
        loglevel = options['loglevel']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting Celery beat scheduler with loglevel={loglevel}')
        )
        
        # Ensure Django settings are set
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configurations.settings')
        
        cmd = [
            sys.executable, '-m', 'celery',
            '-A', 'configurations',
            'beat',
            '--loglevel', loglevel,
            '--scheduler', 'django_celery_beat.schedulers:DatabaseScheduler'
        ]
        
        try:
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Beat scheduler stopped by user'))
        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.ERROR(f'Beat scheduler failed with exit code {e.returncode}')
            ) 