from assets.services import get_content_type_and_asset_id
from configurations.base_features.exceptions.base_exceptions import LocalBaseException
from configurations.base_features.views.base_api_view import BaseAPIView
from assets.models import *
from assets.platforms.base.serializers import *
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType


class AssetBaseView(BaseAPIView):
    serializer_class = AssetBaseSerializer
    model_class = Equipment
    http_method_names = ["get"]

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
    


class EquipmentBaseView(BaseAPIView):
    serializer_class = EquipmentBaseSerializer
    model_class = Equipment


class AttachmentBaseView(BaseAPIView):
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
    http_method_names = ["post", "get"]

    def create(self, request, *args, **kwargs):
        model = kwargs.get("model")
        asset_id = kwargs.get("pk")

        try:
            content_type = ContentType.objects.get(model=model.lower())
            model_class = content_type.model_class()

            if not hasattr(model_class, "location"):
                raise LocalBaseException(
                    _("Model is not a movable asset."), debug_info={"model": model}
                )

            asset = model_class.objects.get(id=asset_id)

            serializer = self.get_serializer(
                data=request.data,
                context={"asset": asset, "request": request}
            )
            serializer.is_valid(raise_exception=True)
            log = serializer.save()

            return self.format_response(
                data={"log_id": str(log.id), "asset_id": str(asset.id)},
                message=_("Asset moved successfully."),
                status_code=200
            )

        except ContentType.DoesNotExist:
            raise LocalBaseException(_("Invalid asset type."), debug_info={"model": model})

        except model_class.DoesNotExist:
            raise LocalBaseException(_("Asset not found."), debug_info={"id": asset_id})