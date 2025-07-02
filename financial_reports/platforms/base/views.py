from assets.services import get_assets_by_gfk
from configurations.base_features.views.base_api_view import BaseAPIView

from financial_reports.models import *
from financial_reports.platforms.base.serializers import *

class CapitalCostBaseView(BaseAPIView):
    serializer_class = CapitalCostBaseSerializer
    model_class = CapitalCost

    def get_instance(self, pk, params=None):        
        return get_assets_by_gfk(self.model_class, pk).first()

