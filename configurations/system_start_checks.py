

from django.conf import settings
from core.models import Domain, Tenant, WorkOrderStatusControls
from scheduled_maintenance.models import SmIttirationCycleChecklist
from django_tenants.utils import schema_context

from tenant_users.models import TenantUser

def public_tenant_check():
    try:
        tenant = Tenant.objects.filter(schema_name='public')
        if not tenant.exists():
            # create your public tenant
            tenant = Tenant(schema_name='public',
                            name='Tenmil Inc.',
                            paid_until='2100-12-05',
                            on_trial=False)
            tenant.save()

            # Add one or more domains for the tenant
            domain = Domain()
            domain.domain = f"{settings.BASE_DOMAIN}" # don't add your port or www here! on a local server you'll want to use localhost here
            domain.tenant = tenant
            domain.is_primary = True
            domain.save()

            # create your schema tenant
            tenant = Tenant(schema_name='tenmil',
                            name='Tenmil Inc.',
                            paid_until='2100-12-05',
                            on_trial=False)
            tenant.save()

            # Add one or more domains for the tenant
            domain = Domain()
            domain.domain = f"tenmil.{settings.BASE_DOMAIN}" # don't add your port or www here! on a local server you'll want to use localhost here
            domain.tenant = tenant
            domain.is_primary = True
            domain.save()
    except:
        pass


def work_order_status_actions_check():
    """
        all work order status actions should be added here
    """
    default_actions = [
        {
            "key": "active",
            "name": "Active",
            "color": "#4caf50",
            "order": 1
        },
        {
            "key": "closed",
            "name": "Closed",
            "color": "#f44336",
            "order": 2
        },
        {
            "key": "draft",
            "name": "Draft",
            "color": "#9e9e9e",
            "order": 3
        },
        {
            "key": "pending",
            "name": "Pending",
            "color": "#2196f3",
            "order": 4
        }
    ]
    for action in default_actions:
        WorkOrderStatusControls.objects.get_or_create(**action)

def ittiration_cycle_checklist():
    """
    """
    default_checklist = ['Checklist Item 1', 'Checklist Item 2', 'Checklist Item 3', 'Checklist Item 4']
    for checklist in default_checklist:
        for tenant in Tenant.objects.exclude(schema_name='public'):
            with schema_context(tenant.schema_name):
                SmIttirationCycleChecklist.objects.get_or_create(name=checklist)

def system_user():
    tenants = Tenant.objects.all()
    for tenant in tenants:
        if tenant.schema_name != 'public':
            with schema_context(tenant.schema_name):
                try:
                    user = TenantUser.objects.get(email=f'Sys_Admin@{tenant.schema_name}.tenmil.ca')
                except TenantUser.DoesNotExist:
                    user = TenantUser.objects.create_user(email=f'Sys_Admin@{tenant.schema_name}.tenmil.ca', name="System Admin", password='admin', tenant=tenant)
                user.is_superuser = True
                user.is_staff = True
                user.save()

def system_start_checks():   
    """
        all project setup steps should be added here
    """
    try:
        public_tenant_check()
        work_order_status_actions_check()
        ittiration_cycle_checklist()
        system_user()
        print("system_start_checks succeed")
    except:
        pass