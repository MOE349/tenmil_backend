from django.conf import settings
from django.shortcuts import HttpResponse

from configurations.base_features.serializers.base_serializer import BaseSerializer
from configurations.base_features.views.base_api_view import BaseAPIView
from core.models import Domain, Tenant

def index(request):
   
    return HttpResponse(f"{request.tenant.name} INDEX")

class TenantSerializer(BaseSerializer):
    class Meta:
        model = Tenant
        fields = '__all__'

class TenantView(BaseAPIView):
    model_class = Tenant
    serializer_class = TenantSerializer
    http_method_names = ['get', 'patch', 'delete', 'post']

    def create(self, request, *args, **kwargs):
        payload = request.data.copy()
        tenant_keys = ['name', 'schema_name', 'paid_until', 'on_trial']
        domain_keys = ['is_primary']

        tenant_payload = {}
        domain_payload = {}

        for field_name, data in payload.items():
            if field_name in tenant_keys:
                tenant_payload[field_name] = data
            elif field_name in domain_keys:
                domain_payload[field_name] = data
            else:
                payload.pop(field_name)
        tenant = Tenant.objects.create(**tenant_payload)
        tenant.save()
        domain_payload['domain'] = f"{tenant.schema_name}.{settings.BASE_DOMAIN}"
        domain_payload['tenant'] = tenant
        domain = Domain.objects.create(**domain_payload)
        domain.save()
        response = {
            'id': str(tenant.id),
            'schema_name': tenant.schema_name,
            'paid_until': tenant.paid_until,
            'on_trial': tenant.on_trial,
            'name': tenant.name,
            'domain': domain.domain,
            'is_primary': domain.is_primary

        }
        return self.format_response(response, status_code=201)