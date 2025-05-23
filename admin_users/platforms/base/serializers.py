from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from admin_users.models import AdminUser
from configurations.base_features.serializers.base_serializer import BaseSerializer

class AdminTokenObtainPairBaseSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['name'] = user.name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['email'] = self.user.email
        data['name'] = self.user.name
        return data

class AdminRegisterBaseSerializer(BaseSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = AdminUser
        fields = ('email', 'name', 'password')

    def create(self, validated_data):
        return AdminUser.objects.create_user(**validated_data)
