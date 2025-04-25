from django.urls import path
from financial_reports.platforms.api.views import *


urlpatterns = [
path('', CapitalCostApiView.as_view(), name='Financial Report'),
path('<str:pk>', CapitalCostApiView.as_view(), name='Financial Report By Asset'),

]