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
        subdomain_parts = host.replace(settings.BASE_DOMAIN, "").rstrip(".").split(".")
        
        logger.error(f"is {host} base domain = {host == settings.BASE_DOMAIN}")
        if host == settings.BASE_DOMAIN:
            logger.error("Admin subdomain found in request")
            # api.alfrih.com → public schema
            request.tenant = None
            request.schema_name = "public"
            connection.set_schema_to_public()
            return

        if host.endswith(f".{settings.BASE_DOMAIN}"):
            logger.error("Tenant subdomain found in request")
            # e.g. client1.api.alfrih.com → subdomain = "client1"
            subdomain = subdomain_parts[0]

            try:
                tenant = Tenant.objects.get(schema_name=subdomain)
                request.tenant = tenant
                request.schema_name = tenant.schema_name
                connection.set_tenant(tenant)
                connection.set_schema(tenant.schema_name)
                return
            except Tenant.DoesNotExist:
                logger.warning(f"[MultiTenancy] Invalid subdomain: '{subdomain}' from host '{host}'")
                return HttpResponse("Invalid tenant subdomain.", status=404)

        # fallback
        connection.set_schema_to_public()
        request.tenant = None
        request.schema_name = "public"