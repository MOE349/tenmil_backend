from django.urls import path
from scheduled_maintenance.platforms.api.views import *


urlpatterns = [
path('scheduled_maintenance', ScheduledMaintenanceApiView.as_view(), name='ScheduledMaintenance'), 
path('sm_ittiration_cycle', SmIttirationCycleApiView.as_view(), name='SmIttirationCycle'), 
path('sm_ittiration_checklist', SmIttirationCycleChecklistApiView.as_view(), name='SmIttirationChecklist'), 
path('sm_log', SmLogApiView.as_view(), name='SmLog'), 
path('get-info', SMInfoApiView.as_view(), name='SMInfo'),
path("create/<str:trigger_type>", ScheduledMaintenanceBaseView.as_view(), name='ScheduledMaintenanceBase'), # meter_reading_triggers || time_triggers
# path("circle_types"),
]