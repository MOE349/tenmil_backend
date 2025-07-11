from configurations.base_features.views.base_api_view import BaseAPIView
from fault_codes.models import *
from fault_codes.platforms.base.serializers import *


class FaultCodeBaseView(BaseAPIView):
    serializer_class = FaultCodeBaseSerializer
    model_class = FaultCode

    def handle_post_data(self, request):
        data = super().handle_post_data(request)
        data['created_by'] = request.user.id
        return data
