from configurations.base_features.serializers.base_serializer import BaseSerializer
from fault_codes.models import *
from tenant_users.platforms.base.serializers import TenantUserBaseSerializer


class FaultCodeBaseSerializer(BaseSerializer):
    class Meta:
        model = FaultCode
        fields = '__all__'


    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['created_by'] = TenantUserBaseSerializer(instance.created_by).data
        return response