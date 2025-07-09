from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from core.models import Tenant
from django.db import connection
import logging

logger = logging.getLogger("django")

class SubdomainTenantMiddleware(MiddlewareMixin):
    """
    Middleware that extracts the tenant from the request's subdomain.
    Sets:
      - request.tenant
      - request.schema_name
      - request.is_admin_subdomain
      - request.tenant_features (optional future use)

    Also applies schema switching (if not handled by django-tenants).
    """

    def process_request(self, request):
        host = request.get_host().split(":")[0]
        subdomain = host.split(".")[0]

        # Determine if admin or main/base domain
        request.is_admin_subdomain = (
            host == settings.BASE_DOMAIN or host.endswith(f".{settings.BASE_DOMAIN}")
        )

        if request.is_admin_subdomain:
            request.tenant = None
            request.schema_name = "public"
            connection.set_schema_to_public()
            return

        try:
            tenant = Tenant.objects.get(schema_name=subdomain)
            request.tenant = tenant
            request.schema_name = tenant.schema_name

            # Optional: apply schema manually if you're not using django-tenants middleware
            connection.set_tenant(tenant)

            # Optional: preload tenant feature flags or limits
            request.tenant_features = {
                "enable_reports": True,
                "max_users": 10,
                # optionally fetch from DB later
            }
            print(f"Tenant found: {tenant.name} on subdomain{subdomain}")
            logger.warning(f"Tenant found: {tenant.name} on subdomain{subdomain}")
        except Tenant.DoesNotExist:
            logger.warning(f"[MultiTenancy] Invalid subdomain: '{subdomain}' from host '{host}'")
            return HttpResponse("Invalid tenant subdomain.", status=404)

        except Exception as e:
            logger.exception(f"[MultiTenancy] Tenant resolution error for host '{host}': {str(e)}")
            return HttpResponse("Internal server error.", status=500)
