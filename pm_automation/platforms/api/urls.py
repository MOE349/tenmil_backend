from django.urls import path
from pm_automation.platforms.api.views import *


urlpatterns = [
    path('pm-settings', PMSettingsApiView.as_view(), name='PM Settings'),
    path('pm-settings/<str:pk>', PMSettingsApiView.as_view(), name='PM Settings'),
    path('pm-triggers', PMTriggerApiView.as_view(), name='PM Triggers'),
    path('pm-triggers/<str:pk>', PMTriggerApiView.as_view(), name='PM Triggers'),
    path('pm-iterations', PMIterationApiView.as_view(), name='PM Iterations'),
    path('pm-iterations/<str:pk>', PMIterationApiView.as_view(), name='PM Iterations'),
    path('pm-iteration-checklist', PMIterationChecklistApiView.as_view(), name='PM Iteration Checklist'),
    path('pm-iteration-checklist/<str:pk>', PMIterationChecklistApiView.as_view(), name='PM Iteration Checklist'),
    
    # Manual PM generation endpoint
    path('pm-settings/<str:pm_settings_id>/manual-generation', ManualPMGenerationApiView.as_view(), name='Manual PM Generation'),
]