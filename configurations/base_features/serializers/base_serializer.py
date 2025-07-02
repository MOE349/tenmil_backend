from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from typing import OrderedDict
from django.conf import settings


class BaseSerializer(ModelSerializer):
    """
    Tenmil base serializer for all models. Includes:
    - Clean mod_ override points (mod_create, mod_update, mod_to_representation)
    - Automatic exclusion of internal fields
    - Extra context handling
    - Consistent base layout for all serializers
    """

    class Meta:
        model = None
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")  # can be overridden

    # -------------------------------
    # Internal: do not override these
    # -------------------------------

    def create(self, validated_data):
        instance = self.mod_create(validated_data)
        return instance

    def update(self, instance, validated_data):
        instance = self.mod_update(instance, validated_data)
        return instance

    def to_representation(self, instance) -> OrderedDict:
        representation = self.mod_to_representation(instance)

        # Optional: auto-strip internal fields if desired
        if hasattr(self.Meta, "strip_internal_fields") and self.Meta.strip_internal_fields:
            internal_fields = ["is_deleted"]
            for f in internal_fields:
                representation.pop(f, None)

        return representation

    # -------------------------------
    # You should override these below
    # -------------------------------

    def mod_create(self, validated_data):
        return super().create(validated_data)

    def mod_update(self, instance, validated_data):
        return super().update(instance, validated_data)

    def mod_to_representation(self, instance):
        return super().to_representation(instance)

    # -------------------------------
    # Helpers
    # -------------------------------

    def get_request(self):
        return self.context.get("request")

    def get_user(self):
        request = self.get_request()
        return getattr(request, "user", None)

    def get_tenant(self):
        request = self.get_request()
        return getattr(request, "tenant", None)

    def is_admin(self):
        return getattr(self.get_request(), "is_admin_subdomain", False)

    def debug_log(self, label, value):
        if settings.DEBUG:
            print(f"[{self.__class__.__name__}] {label} → {value}")
