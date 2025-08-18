from django.core.management.base import BaseCommand
from django.db.models import F
from parts.models import InventoryBatch


class Command(BaseCommand):
    help = 'Fix qty_received values in InventoryBatch records to match current qty_on_hand where needed'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        self.stdout.write('=== Fixing qty_received values ===')
        
        # Check current state
        total_batches = InventoryBatch.objects.count()
        zero_qty_received = InventoryBatch.objects.filter(qty_received=0).count()
        
        self.stdout.write(f'Total inventory batches: {total_batches}')
        self.stdout.write(f'Batches with qty_received=0: {zero_qty_received}')
        
        if zero_qty_received == 0:
            self.stdout.write(self.style.SUCCESS('No records need fixing!'))
            return
        
        # Show sample problematic records
        self.stdout.write('\n=== Sample records that need fixing ===')
        for batch in InventoryBatch.objects.filter(qty_received=0)[:5]:
            self.stdout.write(
                f'Batch {batch.id}: part={batch.part.part_number}, '
                f'location={batch.location.name}, '
                f'qty_received={batch.qty_received}, qty_on_hand={batch.qty_on_hand}'
            )
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('\n[DRY RUN] Would update qty_received=qty_on_hand for these records'))
            return
        
        # Confirmation
        if not options['force']:
            confirm = input(f'\nUpdate qty_received for {zero_qty_received} records? (y/N): ')
            if confirm.lower() != 'y':
                self.stdout.write('Cancelled.')
                return
        
        # Update records
        updated = InventoryBatch.objects.filter(qty_received=0).update(
            qty_received=F('qty_on_hand')
        )
        
        self.stdout.write(self.style.SUCCESS(f'Updated {updated} records'))
        
        # Show sample fixed records
        self.stdout.write('\n=== Sample fixed records ===')
        for batch in InventoryBatch.objects.all()[:5]:
            self.stdout.write(
                f'Batch {batch.id}: part={batch.part.part_number}, '
                f'qty_received={batch.qty_received}, qty_on_hand={batch.qty_on_hand}'
            )
        
        self.stdout.write(self.style.SUCCESS('\n=== Done ==='))
