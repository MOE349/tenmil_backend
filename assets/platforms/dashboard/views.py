from assets.platforms.base.views import *
from assets.platforms.dashboard.serializers import *


class EquipmentDashboardView(EquipmentBaseView):
    serializer_class = EquipmentDashboardSerializer


class AttachmentDashboardView(AttachmentBaseView):
    serializer_class = AttachmentDashboardSerializer


