from django.urls import path
from meter_readings.platforms.api.views import *


urlpatterns = [
path('meter_reading', MeterreadingApiView.as_view(), name='Meter Reading'), 
path('meter_reading/<str:pk>', MeterreadingApiView.as_view(), name='Meter Reading'), 

]