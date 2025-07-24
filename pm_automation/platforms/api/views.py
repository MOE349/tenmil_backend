from pm_automation.platforms.base.views import *
from pm_automation.platforms.api.serializers import *


class PMSettingsApiView(PMSettingsBaseView):
    serializer_class = PMSettingsApiSerializer


class PMTriggerApiView(PMTriggerBaseView):
    serializer_class = PMTriggerApiSerializer


class PMIterationApiView(PMIterationBaseView):
    serializer_class = PMIterationApiSerializer
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to log all requests"""
        print(f"=== REQUEST DISPATCH DEBUG ===")
        print(f"Request method: {request.method}")
        print(f"Request path: {request.path}")
        print(f"Request URL: {request.build_absolute_uri()}")
        print(f"Request headers: {dict(request.headers)}")
        print(f"=============================")
        return super().dispatch(request, *args, **kwargs)
    
    def delete(self, request, pk, *args, **kwargs):
        """Override delete method to add debugging"""
        print(f"=== DELETE METHOD CALLED ===")
        print(f"Request method: {request.method}")
        print(f"Iteration ID: {pk}")
        print(f"============================")
        
        return super().delete(request, pk, *args, **kwargs)


class PMIterationChecklistApiView(PMIterationChecklistBaseView):
    serializer_class = PMIterationChecklistApiSerializer


