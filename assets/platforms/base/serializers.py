from company.models import Location
from company.platforms.base.serializers import LocationBaseSerializer
from configurations.base_features.serializers.base_serializer import BaseSerializer
from configurations.mixins.file_attachment_mixins import FileAttachmentSerializerMixin
from assets.models import *
from projects.platforms.base.serializers import ProjectBaseSerializer, AccountCodeBaseSerializer, JobCodeBaseSerializer, AssetStatusBaseSerializer

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from tenant_users.platforms.base.serializers import TenantUserBaseSerializer

class AssetBaseSerializer(FileAttachmentSerializerMixin, BaseSerializer):
    # def mod_create(self, validated_data):
    #     instance = 
    

    def mod_to_representation(self, instance):
        response = super().mod_to_representation(instance)
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
        # Use serializers for project, account_code, job_code, asset_status
        response['project'] = None
        if getattr(instance, 'project', None):
            response['project'] = ProjectBaseSerializer(instance.project).data
        response['account_code'] = None
        if getattr(instance, 'account_code', None):
            response['account_code'] = AccountCodeBaseSerializer(instance.account_code).data
        response['job_code'] = None
        if getattr(instance, 'job_code', None):
            response['job_code'] = JobCodeBaseSerializer(instance.job_code).data
        response['asset_status'] = None
        if getattr(instance, 'asset_status', None):
            response['asset_status'] = AssetStatusBaseSerializer(instance.asset_status).data
        response['created_at'] = instance.created_at
        response['updated_at'] = instance.updated_at
        response['purchase_date'] = instance.purchase_date
        
        # FileAttachmentSerializerMixin automatically adds:
        # - image: Complete image information
        # - files: File counts, endpoints, upload examples
        
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

    def mod_to_representation(self, instance): 
        response = super().mod_to_representation(instance)
        response['type'] = 'equipment'
        response['weight_class'] = EquipmentWeightClassBaseSerializer(instance.weight_class).data if instance.weight_class else None
        return response


class AttachmentBaseSerializer(AssetBaseSerializer):
    class Meta:
        model = Attachment
        fields = '__all__'

    def mod_to_representation(self, instance): 
        response = super().mod_to_representation(instance)
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
    class Meta:
        model = AssetMovementLog
        fields = '__all__'

    def mod_to_representation(self, instance):
        response = super().mod_to_representation(instance)
        response['from_location'] = LocationBaseSerializer(instance.from_location).data if instance.from_location else None
        response['to_location'] = LocationBaseSerializer(instance.to_location).data if instance.to_location else None
        response['moved_by'] = TenantUserBaseSerializer(instance.moved_by).data if instance.moved_by else None
        return response