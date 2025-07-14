from django.urls import path
from pm_automation.platforms.api.views import *


urlpatterns = [
    path('pm-settings', PMSettingsApiView.as_view(), name='PM Settings'),
    path('pm-settings/<str:pk>', PMSettingsApiView.as_view(), name='PM Settings'),
    path('pm-triggers', PMTriggerApiView.as_view(), name='PM Triggers'),
    path('pm-triggers/<str:pk>', PMTriggerApiView.as_view(), name='PM Triggers'),
]