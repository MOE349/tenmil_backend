from typing import OrderedDict
from rest_framework.serializers import ModelSerializer


class BaseSerializer(ModelSerializer):
    class Meta:
        model = None
        fields = "__all__"

    # DON'T OVERRIDE THOSE METHODS

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return super().to_representation(instance)

    # OVERRIDE THOSE INSTEAD

    def mod_create(self, validated_data):
        return self.create(validated_data)

    def mod_update(self, instance, validated_data):
        return self.update(instance, validated_data)

    def mod_to_representation(self, instance):
        return self.to_representation(instance)
