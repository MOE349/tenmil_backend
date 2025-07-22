from django.urls import path
from pm_automation.platforms.dashboard.views import *


urlpatterns = [
path('pmsettings', PmsettingsDashboardView.as_view(), name='Pmsettings'), 
path('pmtrigger', PmtriggerDashboardView.as_view(), name='Pmtrigger'), 
path('pm-settings-checklist', PMSettingsChecklistDashboardView.as_view(), name='PM Settings Checklist'),
path('pm-settings-checklist/<str:pk>', PMSettingsChecklistDashboardView.as_view(), name='PM Settings Checklist'),
]