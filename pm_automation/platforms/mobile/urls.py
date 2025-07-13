from django.urls import path
from pm_automation.platforms.mobile.views import *

urlpatterns = [
    path('pm-settings/', PMSettingsMobileView.as_view(), name='pm_settings_mobile'),
    path('pm-settings/<uuid:pk>/', PMSettingsMobileView.as_view(), name='pm_settings_detail_mobile'),
    path('pm-triggers/', PMTriggerMobileView.as_view(), name='pm_triggers_mobile'),
    path('pm-triggers/<uuid:pk>/', PMTriggerMobileView.as_view(), name='pm_triggers_detail_mobile'),
]