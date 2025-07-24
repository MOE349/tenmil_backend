from django.urls import path
from pm_automation.platforms.dashboard.views import *


urlpatterns = [
    path('pm-settings', PMSettingsDashboardView.as_view(), name='PM Settings'),
    path('pm-settings/<str:pk>', PMSettingsDashboardView.as_view(), name='PM Settings'),
    path('pm-triggers', PMTriggerDashboardView.as_view(), name='PM Triggers'),
    path('pm-triggers/<str:pk>', PMTriggerDashboardView.as_view(), name='PM Triggers'),
    path('pm-iterations', PMIterationDashboardView.as_view(), name='PM Iterations'),
    path('pm-iterations/<str:pk>', PMIterationDashboardView.as_view(), name='PM Iterations'),
    path('pm-iteration-checklist', PMIterationChecklistDashboardView.as_view(), name='PM Iteration Checklist'),
    path('pm-iteration-checklist/<str:pk>', PMIterationChecklistDashboardView.as_view(), name='PM Iteration Checklist'),
]