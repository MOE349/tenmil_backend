from django.urls import path
from pm_automation.platforms.dashboard.views import *


urlpatterns = [
path('pmsettings', PmsettingsDashboardView.as_view(), name='Pmsettings'), 
path('pmtrigger', PmtriggerDashboardView.as_view(), name='Pmtrigger'), 

]