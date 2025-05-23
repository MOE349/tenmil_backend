from django.urls import path
from scheduled_maintenance.platforms.mobile.views import *


urlpatterns = [
path('scheduled_maintenance', ScheduledMaintenanceMobileView.as_view(), name='ScheduledMaintenance'), 

]