from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from core.models import Tenant, Domain
from django_tenants.utils import get_tenant
import logging

logger = logging.getLogger("django")

class SubdomainTenantMiddleware(MiddlewareMixin):
    """
    Middleware that validates tenant access and sets custom request attributes.
    This runs AFTER django-tenants middleware has already set the tenant.
    """

    def process_request(self, request):
        host = request.get_host().split(":")[0]
        subdomain = host.split(".")[0]

        # Determine if admin or main/base domain
        request.is_admin_subdomain = (
            host == settings.BASE_DOMAIN or host.endswith(f".{settings.BASE_DOMAIN}")
        )

        if request.is_admin_subdomain:
            # For admin domain, ensure we're in public schema
            request.tenant = None
            request.schema_name = "public"
            return

        # Get the tenant that django-tenants has already set
        try:
            tenant = get_tenant(request)
            
            # Check if tenant exists and validate it matches the subdomain
            if tenant is None:
                logger.warning(f"[MultiTenancy] No tenant found for subdomain: '{subdomain}' from host '{host}'")
                return HttpResponse("Invalid tenant subdomain.", status=404)
            
            if tenant.schema_name != subdomain:
                logger.warning(f"[MultiTenancy] Tenant mismatch: expected '{subdomain}', got '{tenant.schema_name}' from host '{host}'")
                return HttpResponse("Invalid tenant subdomain.", status=404)
            
            # Set additional request attributes
            request.tenant = tenant
            request.schema_name = tenant.schema_name

            # Optional: preload tenant feature flags or limits
            request.tenant_features = {
                "enable_reports": True,
                "max_users": 10,
                # optionally fetch from DB later
            }

        except Exception as e:
            logger.exception(f"[MultiTenancy] Tenant validation error for host '{host}': {str(e)}")
            return HttpResponse("Internal server error.", status=500)
