import traceback
from django.shortcuts import HttpResponse
from rest_framework_simplejwt.views import TokenRefreshView
from configurations.base_features.views.base_exception_handler import BaseExceptionHandlerMixin
from configurations.base_features.views.base_response import ResponseFormatterMixin
from core.models import Tenant, Domain
from django.conf import settings

def index(request):
    is_system_ready = Tenant.objects.exists()
    if not is_system_ready:

        # create your public tenant
        tenant = Tenant(schema_name='public',
                        name='Schemas Inc.',
                        paid_until='2025-12-05',
                        on_trial=False)
        tenant.save()

        # Add one or more domains for the tenant
        domain = Domain()
        domain.domain = settings.BASE_DOMAIN # don't add your port or www here! on a local server you'll want to use localhost here
        domain.tenant = tenant
        domain.is_primary = True
        domain.save()
    return HttpResponse(f"{request.tenant.name} INDEX")

class TokenSliding(TokenRefreshView, BaseExceptionHandlerMixin, ResponseFormatterMixin):
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            print(response.data)
            token = response.data['access']
            response =  {
                'access_token': str(token),
            }
            return self.format_response(response, status_code=200)
        except Exception as e:
            traceback.print_exc()
            return self.handle_exception(e)