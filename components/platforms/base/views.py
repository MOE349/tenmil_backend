from configurations.base_features.views.base_api_view import BaseAPIView
from configurations.base_features.exceptions.base_exceptions import LocalBaseException
from components.models import *
from components.platforms.base.serializers import *


class ComponentBaseView(BaseAPIView):
    serializer_class = ComponentBaseSerializer
    model_class = Component

    
