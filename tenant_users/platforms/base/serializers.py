from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from configurations.base_features.serializers.base_serializer import BaseSerializer
from tenant_users.models import TenantUser


class TenantUserBaseSerializer(BaseSerializer):
    class Meta:
        model = TenantUser
        fields = ('id', 'email', 'name', 'tenant')

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['tenant'] = instance.tenant.name
        return response


class TenantTokenObtainPairBaseSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['name'] = user.name
        token['tenant_id'] = user.tenant_id
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['email'] = self.user.email
        data['name'] = self.user.name
        data['tenant_id'] = self.user.tenant_id
        return data

class TenantRegisterBaseSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = TenantUser
        fields = ('email', 'name', 'password')

    def create(self, validated_data):
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        print(tenant)
        if not tenant:
            raise serializers.ValidationError("Tenant context is required.")
        return TenantUser.objects.create_user(tenant=tenant, **validated_data)