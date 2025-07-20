from django.urls import path
from projects.platforms.mobile.views import *


urlpatterns = [
path('project', ProjectMobileView.as_view(), name='Project'), 
path('account_code', AccountCodeMobileView.as_view(), name='AccountCode'), 
path('job_code', JobCodeMobileView.as_view(), name='JobCode'), 
path('asset_status', AssetStatusMobileView.as_view(), name='AssetStatus'), 

]