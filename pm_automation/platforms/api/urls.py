from django.urls import path
from pm_automation.platforms.api.views import *

urlpatterns = [
    path('pm-settings/', PMSettingsApiView.as_view(), name='pm_settings_api'),
    path('pm-settings/<uuid:pk>/', PMSettingsApiView.as_view(), name='pm_settings_detail_api'),
    path('pm-triggers/', PMTriggerApiView.as_view(), name='pm_triggers_api'),
    path('pm-triggers/<uuid:pk>/', PMTriggerApiView.as_view(), name='pm_triggers_detail_api'),
]