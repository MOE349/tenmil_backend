from django.core.management.base import BaseCommand
from django.core.management import execute_from_command_line
from django_tenants.utils import tenant_context
from core.models import Tenant
import sys


class Command(BaseCommand):
    help = "Start Django shell with tenant context"

    def add_arguments(self, parser):
        parser.add_argument(
            '--tenant',
            type=str,
            help='Tenant schema name (e.g., tenmil)',
            required=True
        )

    def handle(self, *args, **options):
        tenant_name = options['tenant']
        
        try:
            tenant = Tenant.objects.get(schema_name=tenant_name)
        except Tenant.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Tenant "{tenant_name}" does not exist')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'Starting shell for tenant: {tenant_name}')
        )
        
        # Import commonly used models in tenant context
        with tenant_context(tenant):
            from parts.models import Part, InventoryBatch, WorkOrderPart, PartMovement
            from work_orders.models import WorkOrder
            from assets.models import Equipment, Attachment
            from company.models import Location
            from tenant_users.models import TenantUser
            
            # Make these available in shell
            shell_locals = {
                'tenant': tenant,
                'Part': Part,
                'InventoryBatch': InventoryBatch,
                'WorkOrderPart': WorkOrderPart,
                'PartMovement': PartMovement,
                'WorkOrder': WorkOrder,
                'Equipment': Equipment,
                'Attachment': Attachment,
                'Location': Location,
                'TenantUser': TenantUser,
            }
            
            # Start IPython shell if available, otherwise use default
            try:
                from IPython import start_ipython
                start_ipython(argv=[], user_ns=shell_locals)
            except ImportError:
                import code
                code.interact(local=shell_locals)
