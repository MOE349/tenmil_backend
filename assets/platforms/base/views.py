from assets.services import get_assets_by_gfk, get_content_type_and_asset_id, move_asset
from configurations.base_features.exceptions.base_exceptions import LocalBaseException
from configurations.base_features.views.base_api_view import BaseAPIView
from assets.models import *
from assets.platforms.base.serializers import *
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType


class AssetBaseView(BaseAPIView):
    serializer_class = AssetBaseSerializer
    model_class = Equipment
    http_method_names = ["get", "patch", "put", "post", "delete"]

    def list(self, request, *args, **kwargs):
        equipments_instance = Equipment.objects.all()
        equipments = list(EquipmentBaseSerializer(equipments_instance, many=True).data)
        attachments_instance = Attachment.objects.all()
        attachments = list(AttachmentBaseSerializer(attachments_instance, many=True).data)
        response = sorted(equipments + attachments, key=lambda x: x['created_at'], reverse=True)
        return self.format_response(data=response, status_code=200)

    def get_instance(self, pk, params=None):
        ct, instance= get_content_type_and_asset_id(pk, return_ct_instance=True, return_instance=True)
        if ct == ContentType.objects.get_for_model(Equipment):
            self.serializer_class = EquipmentBaseSerializer
        elif ct == ContentType.objects.get_for_model(Attachment):
            self.serializer_class = AttachmentBaseSerializer
        else:
            raise LocalBaseException(exception="Invalid asset type.")
        return instance

    def update(self, data, params,  pk, partial, *args, **kwargs):
        print(f"Asset update data: {data}")
        instance, response = super().update(data, params,  pk, partial, *args, **kwargs)    
        if "location" in data:
            print(f"update location: {data['location']}")
            move_asset(asset=instance, to_location=data["location"], user=self.get_request_user(self.request))
        return self.format_response(data=response, status_code=200)
    

class EquipmentWeightClassBaseView(BaseAPIView):
    serializer_class = EquipmentWeightClassBaseSerializer
    model_class = EquipmentWeightClass


class EquipmentBaseView(AssetBaseView):
    serializer_class = EquipmentBaseSerializer
    model_class = Equipment

class AttachmentBaseView(AssetBaseView):
    serializer_class = AttachmentBaseSerializer
    model_class = Attachment


class EquipmentCategoryBaseView(BaseAPIView):
    serializer_class = EquipmentCategoryBaseSerializer
    model_class = EquipmentCategory


class AttachmentCategoryBaseView(BaseAPIView):
    serializer_class = AttachmentCategoryBaseSerializer
    model_class = AttachmentCategory


class AssetBaseMoveView(BaseAPIView):
    serializer_class = AssetMoveBaseSerializer
    model_class = AssetMovementLog
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        try:
            params = self.get_request_params(request)
            instances = self.get_queryset(params=params)
            response = self.serializer_class(instances, many=True).data
            return self.format_response(data=response, status_code=200)
        except Exception as e:
            self.handle_exception(e)


    