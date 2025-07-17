from company.models import Location
from configurations.base_features.serializers.base_serializer import BaseSerializer
from assets.models import *

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

class AssetBaseSerializer(BaseSerializer):
    # def mod_create(self, validated_data):
    #     instance = 
    

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
        if hasattr(instance, 'equipment'):
            response['equipment'] = EquipmentBaseSerializer(instance.equipment).data
        return response


class EquipmentWeightClassBaseSerializer(BaseSerializer):
    class Meta:
        model = EquipmentWeightClass
        fields = '__all__'
        

class EquipmentBaseSerializer(AssetBaseSerializer):
    class Meta:
        model = Equipment
        fields = '__all__'

    def to_representation(self, instance): 
        response = super().to_representation(instance)
        response['type'] = 'equipment'
        return response


class AttachmentBaseSerializer(AssetBaseSerializer):
    class Meta:
        model = Attachment
        fields = '__all__'

    def to_representation(self, instance): 
        response = super().to_representation(instance)
        response['type'] = 'attachment'
        return response


class EquipmentCategoryBaseSerializer(BaseSerializer):
    class Meta:
        model = EquipmentCategory
        fields = '__all__'


class AttachmentCategoryBaseSerializer(BaseSerializer):
    class Meta:
        model = AttachmentCategory
        fields = '__all__'


class AssetMoveBaseSerializer(BaseSerializer):
    to_location = serializers.UUIDField()
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        location_id = attrs.get("to_location")
        location = Location.objects.filter(id=location_id).first()

        if not location:
            raise serializers.ValidationError({"to_location": _("Invalid location ID")})

        attrs["to_location_obj"] = location
        return attrs

    def mod_create(self, validated_data):
        # Should be called from the BaseApiView `create()` method
        asset = self.context.get("asset")
        user = self.context.get("request").user
        to_location = validated_data["to_location_obj"]
        notes = validated_data.get("notes", "")

        from assets.services import move_asset
        return move_asset(asset, to_location, notes=notes, user=user)
