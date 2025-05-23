from django.urls import path
from scheduled_maintenance.platforms.dashboard.views import *


urlpatterns = [
path('scheduled_maintenance', ScheduledMaintenanceDashboardView.as_view(), name='ScheduledMaintenance'), 

]