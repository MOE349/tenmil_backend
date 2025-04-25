from assets.models import Attachment, Equipment
from configurations.base_features.views.base_api_view import BaseAPIView
from configurations.base_features.exceptions.base_exceptions import LocalBaseException

from financial_reports.models import *
from financial_reports.platforms.base.serializers import *

class CapitalCostBaseView(BaseAPIView):
    serializer_class = CapitalCostBaseSerializer
    model_class = CapitalCost

    def get_instance(self, pk=None, params=None):
        
        print(pk)
        # try:
        #     asset_instance, errors, status_code = Equipment.objects.get_object_or_404(id=pk, raise_exception=True)
        #     print('equipment found', asset_instance)
        # except:
        #     print('equipment not found')
        #     asset_instance = Attachment.objects.get_object_or_404(id=pk, raise_exception=True)
        #     print('attachment found')
        asset = Asset.objects.get_object_or_404(id=pk, raise_exception=True)
        capital_cost_args = {"asset":asset}

        instance_object = self.model_class.objects.get_object_or_404(**capital_cost_args, raise_exception=True)
        return instance_object

