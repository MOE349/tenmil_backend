from django.urls import path
from fault_codes.platforms.dashboard.views import *


urlpatterns = [
path('fault_code', FaultCodeDashboardView.as_view(), name='FaultCode'), 

]