from django.urls import path
from meter_readings.platforms.mobile.views import *


urlpatterns = [
path('MeterReading', MeterreadingMobileView.as_view(), name='Meterreading'), 

]