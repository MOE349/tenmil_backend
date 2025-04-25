from django.urls import path
from meter_readings.platforms.dashboard.views import *


urlpatterns = [
path('MeterReading', MeterreadingDashboardView.as_view(), name='Meterreading'), 

]