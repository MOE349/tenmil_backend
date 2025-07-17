from assets.platforms.base.views import *
from assets.platforms.api.serializers import *


class AssetApiView(AssetBaseView):
    serializer_class = AssetApiSerializer


class EquipmentApiView(EquipmentBaseView):
    serializer_class = EquipmentApiSerializer


class AttachmentApiView(AttachmentBaseView):
    serializer_class = AttachmentApiSerializer


class EquipmentCategoryApiView(EquipmentCategoryBaseView):
    serializer_class = EquipmentCategoryApiSerializer


class AttachmentCategoryApiView(AttachmentCategoryBaseView):
    serializer_class = AttachmentCategoryApiSerializer


class AssetMoveApiView(AssetBaseMoveView):
    serializer_class = AssetMoveApiSerializer

class EquipmentWeightClassApiView(EquipmentWeightClassBaseView):
    serializer_class = EquipmentWeightClassApiSerializer