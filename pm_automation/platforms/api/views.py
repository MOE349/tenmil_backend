from pm_automation.platforms.base.views import *
from pm_automation.platforms.api.serializers import *
from configurations.base_features.exceptions.base_exceptions import LocalBaseException


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
        """Override delete method to prevent deletion of default iteration"""
        print(f"=== DELETE METHOD CALLED ===")
        print(f"Request method: {request.method}")
        print(f"Iteration ID: {pk}")
        print(f"============================")
        
        # Get the iteration to check if it's the default one
        try:
            iteration = PMIteration.objects.get(id=pk)
            
            # Check if this iteration matches the PM settings' interval_value
            if iteration.interval_value == iteration.pm_settings.interval_value:
                raise LocalBaseException(
                    exception="Cannot delete the default iteration that matches the PM settings interval",
                    status_code=400
                )
            
        except PMIteration.DoesNotExist:
            raise LocalBaseException(
                exception="Iteration not found",
                status_code=404
            )
        
        return super().delete(request, pk, *args, **kwargs)


class PMIterationChecklistApiView(PMIterationChecklistBaseView):
    serializer_class = PMIterationChecklistApiSerializer


class ManualPMGenerationApiView(ManualPMGenerationBaseView):
    """API view for manual PM work order generation"""
    pass


