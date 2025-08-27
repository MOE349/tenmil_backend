from configurations.base_features.serializers.base_serializer import BaseSerializer
from company.models import *


class SiteBaseSerializer(BaseSerializer):
    class Meta:
        model = Site
        fields = '__all__'


class LocationBaseSerializer(BaseSerializer):
    class Meta:
        model = Location
        fields = '__all__'

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['site'] = SiteBaseSerializer(instance.site).data
        response["name"] = f"{instance.site.code} - {instance.name}",
        return response

