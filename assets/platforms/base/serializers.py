from company.models import Location
from company.platforms.base.serializers import LocationBaseSerializer
from configurations.base_features.serializers.base_serializer import BaseSerializer
from assets.models import *
from projects.platforms.base.serializers import ProjectBaseSerializer, AccountCodeBaseSerializer, JobCodeBaseSerializer, AssetStatusBaseSerializer

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from tenant_users.platforms.base.serializers import TenantUserBaseSerializer

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
        
        # Add image information
        response['image'] = None
        if instance.image and not instance.image.is_deleted:
            response['image'] = {
                "id": str(instance.image.id),
                "url": instance.image.get_file_url(),
                "original_filename": instance.image.original_filename,
                "file_size": instance.image.file_size,
                "download_url": instance.image.get_download_url()
            }
        
        # Add files information
        files_count = instance.files.not_deleted().count()
        images_count = instance.files.not_deleted().images().count()
        response['files'] = {
            "total_count": files_count,
            "images_count": images_count,
            "documents_count": instance.files.not_deleted().documents().count(),
            "files_endpoint": f"/v1/api/file-uploads/files/?link_to_model=assets.{instance.__class__.__name__.lower()}&link_to_id={instance.id}",
            "upload_endpoint": "/v1/api/file-uploads/files/",
            "set_image_endpoint": f"/v1/api/assets/{instance.__class__.__name__.lower()}/{instance.id}/set-image/"
        }
        
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
        response['weight_class'] = EquipmentWeightClassBaseSerializer(instance.weight_class).data
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
    class Meta:
        model = AssetMovementLog
        fields = '__all__'

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['from_location'] = LocationBaseSerializer(instance.from_location).data
        response['to_location'] = LocationBaseSerializer(instance.to_location).data
        response['moved_by'] = TenantUserBaseSerializer(instance.moved_by).data
        return response