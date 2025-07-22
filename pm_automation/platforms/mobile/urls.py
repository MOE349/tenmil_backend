from django.urls import path
from pm_automation.platforms.mobile.views import *


urlpatterns = [
path('pmsettings', PmsettingsMobileView.as_view(), name='Pmsettings'), 
path('pmtrigger', PmtriggerMobileView.as_view(), name='Pmtrigger'), 
path('pm-settings-checklist', PMSettingsChecklistMobileView.as_view(), name='PM Settings Checklist'),
path('pm-settings-checklist/<str:pk>', PMSettingsChecklistMobileView.as_view(), name='PM Settings Checklist'),
]