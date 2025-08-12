from components.platforms.base.views import *
from components.platforms.api.serializers import *


class ComponentApiView(ComponentBaseView):
    serializer_class = ComponentApiSerializer


