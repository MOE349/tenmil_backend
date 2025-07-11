from django.urls import path
from fault_codes.platforms.mobile.views import *


urlpatterns = [
path('fault_code', FaultCodeMobileView.as_view(), name='FaultCode'), 

]