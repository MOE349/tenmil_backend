from django.db import connection
from django.http import HttpResponse
import logging

from core.models import Domain, TenantMixin

logger = logging.getLogger("django")

class SubdomainTenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0]
        print("Host:", host)

        try:
            domain_name = host.split(".")[0]
            domain = Domain.objects.select_related("tenant").get(domain=domain_name)
            tenant = domain.tenant
            print("Resolved tenant:", tenant, "schema:", tenant.schema_name)
            print("Is instance of TenantMixin:", isinstance(tenant, TenantMixin))
            
            connection.set_tenant(tenant)
            print("Set tenant:", getattr(connection, "tenant", "Not set"))
        except Domain.DoesNotExist:
            connection.set_schema_to_public()
            return HttpResponse("Tenant not found", status=404)

        return self.get_response(request)
