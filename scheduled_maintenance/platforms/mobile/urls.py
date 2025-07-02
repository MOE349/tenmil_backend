from django.urls import path
from scheduled_maintenance.platforms.mobile.views import *


urlpatterns = [
path('scheduled_maintenance', ScheduledMaintenanceMobileView.as_view(), name='ScheduledMaintenance'), 
path('sm_ittiration_cycle', SmIttirationCycleMobileView.as_view(), name='SmIttirationCycle'), 
path('sm_log', SmLogMobileView.as_view(), name='SmLog'), 

]