

from django.conf import settings
from core.models import Domain, Tenant, WorkOrderStatusControls


def public_tenant_check():
    try:
        Tenant.objects.filter(schema_name='public')
    except:
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

def work_order_status_actions_check():
    """
        all work order status actions should be added here
    """
    default_actions = ['Active', 'Closed', 'Draft', 'Pending']
    for action in default_actions:
        WorkOrderStatusControls.objects.get_or_create(name=action)
                

def system_start_checks():   
    """
        all project setup steps should be added here
    """
    public_tenant_check()
    work_order_status_actions_check()
