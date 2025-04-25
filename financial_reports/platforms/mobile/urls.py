from django.urls import path
from financial_reports.platforms.mobile.views import *


urlpatterns = [
path('CapitalCost', CapitalCostMobileView.as_view(), name='CapitalCost'), 

]