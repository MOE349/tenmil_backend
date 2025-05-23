from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from core.models import Tenant
from django.http import HttpResponse

class SubdomainTenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        host = request.get_host().split(':')[0]
        subdomain = host.split('.')[0]

        request.is_admin_subdomain = (subdomain == settings.BASE_DOMAIN)

        if not request.is_admin_subdomain:
            try:
                tenant = Tenant.objects.get(schema_name=subdomain)
                request.tenant = tenant
            except Tenant.DoesNotExist:
                return HttpResponse("Invalid tenant subdomain.", status=404)
        else:
            request.tenant = None  # explicitly clear tenant for admin
