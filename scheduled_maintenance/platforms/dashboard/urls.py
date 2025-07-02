from django.urls import path
from scheduled_maintenance.platforms.dashboard.views import *


urlpatterns = [
path('scheduled_maintenance', ScheduledMaintenanceDashboardView.as_view(), name='ScheduledMaintenance'), 
path('sm_ittiration_cycle', SmIttirationCycleDashboardView.as_view(), name='SmIttirationCycle'), 
path('sm_log', SmLogDashboardView.as_view(), name='SmLog'), 

]