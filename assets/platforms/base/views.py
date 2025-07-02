from configurations.base_features.exceptions.base_exceptions import LocalBaseException
from configurations.base_features.views.base_api_view import BaseAPIView
from assets.models import *
from assets.platforms.base.serializers import *
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType


class EquipmentBaseView(BaseAPIView):
    serializer_class = EquipmentBaseSerializer
    model_class = Equipment


class AttachmentBaseView(BaseAPIView):
    serializer_class = AttachmentBaseSerializer
    model_class = Attachment


class EquipmentCategoryBaseView(BaseAPIView):
    serializer_class = EquipmentCategoryBaseSerializer
    model_class = EquipmentCategory


class AssetBaseMoveView(BaseAPIView):
    serializer_class = AssetMoveBaseSerializer
    model_class = AssetMovementLog
    http_method_names = ["post"]

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