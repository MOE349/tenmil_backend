from configurations.base_features.views.base_api_view import BaseAPIView
from assets.models import *
from assets.platforms.base.serializers import *


class EquipmentBaseView(BaseAPIView):
    serializer_class = EquipmentBaseSerializer
    model_class = Equipment


class AttachmentBaseView(BaseAPIView):
    serializer_class = AttachmentBaseSerializer
    model_class = Attachment


class EquipmentCategoryBaseView(BaseAPIView):
    serializer_class = EquipmentCategoryBaseSerializer
    model_class = EquipmentCategory


