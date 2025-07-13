from django.urls import path
from pm_automation.platforms.dashboard.views import *

urlpatterns = [
    path('pm-settings/', PMSettingsDashboardView.as_view(), name='pm_settings_dashboard'),
    path('pm-settings/<uuid:pk>/', PMSettingsDashboardView.as_view(), name='pm_settings_detail_dashboard'),
    path('pm-triggers/', PMTriggerDashboardView.as_view(), name='pm_triggers_dashboard'),
    path('pm-triggers/<uuid:pk>/', PMTriggerDashboardView.as_view(), name='pm_triggers_detail_dashboard'),
]