from configurations.base_features.serializers.base_serializer import BaseSerializer
from assets.models import *


class EquipmentBaseSerializer(BaseSerializer):
    class Meta:
        model = Equipment
        fields = '__all__'

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['id'] = str(instance.id)
        response['location'] = {
            "id": str(instance.location.id),
            "name": f"{instance.location.name} - {instance.location.site.name}",
            "end_point": "/company/location"
        }
        response['site'] = {
            "id": str(instance.location.site.id),
            "name": instance.location.site.name,
            "end_point": "/company/site"
        }
        response['category'] = {
            "id": str(instance.category.id),
            "name": instance.category.name,
            "slug": instance.category.slug,
            "end_point": "/assets/category"
        }
        response['created_at'] = instance.created_at
        response['updated_at'] = instance.updated_at
        response['purchase_date'] = instance.purchase_date
        return response

class AttachmentBaseSerializer(BaseSerializer):
    class Meta:
        model = Attachment
        fields = '__all__'


class EquipmentCategoryBaseSerializer(BaseSerializer):
    class Meta:
        model = EquipmentCategory
        fields = '__all__'
