from django.http import HttpResponse
from django.db import connection
from django_tenants.models import Domain
import logging

logger = logging.getLogger("django")

class SubdomainTenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0]  # strip port if any

        PUBLIC_DOMAINS = ["api.alfrih.com"]

        if host in PUBLIC_DOMAINS:
            # Treat as shared/public tenant
            request.tenant = None
            request.schema_name = "public"
            connection.set_schema_to_public()
            logger.info(f"[MultiTenancy] '{host}' using public schema")
            return self.get_response(request)

        try:
            domain = Domain.objects.select_related("tenant").get(domain=host)
            tenant = domain.tenant
            connection.set_tenant(tenant)
            request.tenant = tenant
            request.schema_name = tenant.schema_name
            logger.info(f"[MultiTenancy] '{host}' resolved to tenant '{tenant.schema_name}'")
        except Domain.DoesNotExist:
            logger.warning(f"[MultiTenancy] No tenant found for host '{host}'")
            connection.set_schema_to_public()
            request.tenant = None
            request.schema_name = "public"
            return HttpResponse("Tenant not found", status=404)

        return self.get_response(request)
