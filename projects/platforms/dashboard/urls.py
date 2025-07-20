from django.urls import path
from projects.platforms.dashboard.views import *


urlpatterns = [
path('project', ProjectDashboardView.as_view(), name='Project'), 
path('account_code', AccountCodeDashboardView.as_view(), name='AccountCode'), 
path('job_code', JobCodeDashboardView.as_view(), name='JobCode'), 
path('asset_status', AssetStatusDashboardView.as_view(), name='AssetStatus'), 

]