from django.conf import settings
from django_tenants.utils import get_tenant

from admin_users.models import AdminUser
from tenant_users.models import TenantUser

def get_user_model_for_request(request):
    """
    Dynamically returns the correct user model depending on the request's tenant.
    """
    # Admin user if we're in the public schema or admin subdomain
    if getattr(request, 'is_admin_subdomain', False) or get_tenant(request).schema_name == settings.PUBLIC_SCHEMA_NAME:
        return AdminUser
    return TenantUser