from django.core.management.base import BaseCommand
import os
import subprocess
import sys
from django.conf import settings

class Command(BaseCommand):
    help = 'Start Celery worker'

    def add_arguments(self, parser):
        parser.add_argument(
            '--concurrency',
            type=int,
            default=4,
            help='Number of concurrent worker processes'
        )
        parser.add_argument(
            '--loglevel',
            type=str,
            default='INFO',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            help='Logging level'
        )
        parser.add_argument(
            '--queue',
            type=str,
            default='default',
            help='Queue to process (default: all queues)'
        )

    def handle(self, *args, **options):
        concurrency = options['concurrency']
        loglevel = options['loglevel']
        queue = options['queue']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting Celery worker with concurrency={concurrency}, loglevel={loglevel}, queue={queue}')
        )
        
        # Ensure Django settings are set
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configurations.settings')
        
        cmd = [
            sys.executable, '-m', 'celery',
            '-A', 'configurations',
            'worker',
            '--loglevel', loglevel,
            '--concurrency', str(concurrency),
            '--queues', queue
        ]
        
        try:
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Worker stopped by user'))
        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.ERROR(f'Worker failed with exit code {e.returncode}')
            ) 