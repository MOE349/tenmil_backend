from django.urls import path
from scheduled_maintenance.platforms.api.views import *


urlpatterns = [
path('scheduled_maintenance', ScheduledMaintenanceApiView.as_view(), name='ScheduledMaintenance'), 

]