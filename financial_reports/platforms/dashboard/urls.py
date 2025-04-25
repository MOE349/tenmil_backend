from django.urls import path
from financial_reports.platforms.dashboard.views import *


urlpatterns = [
path('CapitalCost', CapitalCostDashboardView.as_view(), name='CapitalCost'), 

]