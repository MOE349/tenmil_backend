from django.urls import path
from meter_readings.platforms.api.views import *


urlpatterns = [
path('', MeterreadingApiView.as_view(), name='Meter Reading'), 

]