from django.urls import path
from pm_automation.platforms.mobile.views import *


urlpatterns = [
    path('pm-settings', PMSettingsMobileView.as_view(), name='PM Settings'),
    path('pm-settings/<str:pk>', PMSettingsMobileView.as_view(), name='PM Settings'),
    path('pm-triggers', PMTriggerMobileView.as_view(), name='PM Triggers'),
    path('pm-triggers/<str:pk>', PMTriggerMobileView.as_view(), name='PM Triggers'),
    path('pm-iterations', PMIterationMobileView.as_view(), name='PM Iterations'),
    path('pm-iterations/<str:pk>', PMIterationMobileView.as_view(), name='PM Iterations'),
    path('pm-iteration-checklist', PMIterationChecklistMobileView.as_view(), name='PM Iteration Checklist'),
    path('pm-iteration-checklist/<str:pk>', PMIterationChecklistMobileView.as_view(), name='PM Iteration Checklist'),
    
    # Manual PM generation endpoint
    path('pm-settings/manual-generation/<str:pm_settings_id>', ManualPMGenerationMobileView.as_view(), name='Manual PM Generation'),
]