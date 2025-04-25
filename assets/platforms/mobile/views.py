from assets.platforms.base.views import *
from assets.platforms.mobile.serializers import *


class EquipmentMobileView(EquipmentBaseView):
    serializer_class = EquipmentMobileSerializer


class AttachmentMobileView(AttachmentBaseView):
    serializer_class = AttachmentMobileSerializer


