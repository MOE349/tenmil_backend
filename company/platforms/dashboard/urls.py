from django.urls import path
from company.platforms.dashboard.views import *


urlpatterns = [
path('site', SiteDashboardView.as_view(), name='Site'), 
path('location', LocationDashboardView.as_view(), name='Location'), 

]