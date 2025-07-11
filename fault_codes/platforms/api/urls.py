from django.urls import path
from fault_codes.platforms.api.views import *


urlpatterns = [
path('codes', FaultCodeApiView.as_view(), name='FaultCode'), 

]