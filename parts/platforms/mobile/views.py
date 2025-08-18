from parts.platforms.base.views import *
from parts.platforms.mobile.serializers import *


class PartMobileView(PartBaseView):
    serializer_class = PartMobileSerializer


class InventorybatchMobileView(InventorybatchBaseView):
    serializer_class = InventorybatchMobileSerializer


class WorkorderpartMobileView(WorkorderpartBaseView):
    serializer_class = WorkorderpartMobileSerializer


class PartmovementMobileView(PartmovementBaseView):
    serializer_class = PartmovementMobileSerializer


