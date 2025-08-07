from assets.platforms.base.views import *
from assets.platforms.api.serializers import *


class AssetApiView(AssetBaseView):
    serializer_class = AssetApiSerializer
    
    def post(self, request, pk=None, action=None, *args, **kwargs):
        """Handle POST requests including custom actions"""
        if action == 'set_image':
            return self.set_image(request, pk, *args, **kwargs)
        return super().post(request, *args, **kwargs)


class EquipmentApiView(EquipmentBaseView):
    serializer_class = EquipmentApiSerializer
    
    def post(self, request, pk=None, action=None, *args, **kwargs):
        """Handle POST requests including custom actions"""
        if action == 'set_image':
            return self.set_image(request, pk, *args, **kwargs)
        return super().post(request, *args, **kwargs)


class AttachmentApiView(AttachmentBaseView):
    serializer_class = AttachmentApiSerializer
    
    def post(self, request, pk=None, action=None, *args, **kwargs):
        """Handle POST requests including custom actions"""
        if action == 'set_image':
            return self.set_image(request, pk, *args, **kwargs)
        return super().post(request, *args, **kwargs)


class EquipmentCategoryApiView(EquipmentCategoryBaseView):
    serializer_class = EquipmentCategoryApiSerializer


class AttachmentCategoryApiView(AttachmentCategoryBaseView):
    serializer_class = AttachmentCategoryApiSerializer


class AssetMoveApiView(AssetBaseMoveView):
    serializer_class = AssetMoveApiSerializer

class EquipmentWeightClassApiView(EquipmentWeightClassBaseView):
    serializer_class = EquipmentWeightClassApiSerializer


class AssetOnlineStatusLogApiView(AssetOnlineStatusLogBaseView):
    serializer_class = AssetOnlineStatusLogApiSerializer