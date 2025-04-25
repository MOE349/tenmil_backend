from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import authenticate, login

from configurations.base_features.exceptions.base_exceptions import LocalBaseException
from configurations.base_features.serializers.base_serializer import BaseSerializer
from users.models import *


class UserBaseSerializer(BaseSerializer):
    class Meta:
        model = User
        fields = ["id", 'email', 'name', 'is_active']


class LoginBaseSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField()

    class Meta:
        model = User
        fields = ['email', 'password']

class RegisterBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'password', 'name']