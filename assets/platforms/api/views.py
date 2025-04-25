from assets.platforms.base.views import *
from assets.platforms.api.serializers import *


class EquipmentApiView(EquipmentBaseView):
    serializer_class = EquipmentApiSerializer


class AttachmentApiView(AttachmentBaseView):
    serializer_class = AttachmentApiSerializer


class EquipmentCategoryApiView(EquipmentCategoryBaseView):
    serializer_class = EquipmentCategoryApiSerializer
