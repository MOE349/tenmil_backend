from configurations.base_features.views.base_api_view import BaseAPIView
from pm_automation.models import *
from pm_automation.platforms.base.serializers import *
from pm_automation.services import PMAutomationService
from rest_framework.response import Response


class PMSettingsBaseView(BaseAPIView):
    serializer_class = PMSettingsBaseSerializer
    model_class = PMSettings

    def get(self, request, *args, **kwargs):
        """Override get to handle asset status query"""
        asset_id = request.query_params.get('asset_id')
        if asset_id:
            # Return asset status
            status = PMAutomationService.get_asset_pm_status(asset_id)
            if not status:
                return Response({'message': 'No PM settings found for this asset'})
            
            return Response({
                'pm_settings_count': status['pm_settings_count'],
                'has_active_settings': status['has_active_settings'],
                'open_work_orders_count': status['open_work_orders'].count(),
                'pending_triggers_count': status['pending_triggers'].count(),
                'pm_settings': PMSettingsBaseSerializer(status['pm_settings'], many=True).data
            })
        
        # Default list behavior
        return super().get(request, *args, **kwargs)


class PMTriggerBaseView(BaseAPIView):
    serializer_class = PMTriggerBaseSerializer
    model_class = PMTrigger


