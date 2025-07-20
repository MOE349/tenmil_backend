from django.urls import path
from projects.platforms.api.views import *


urlpatterns = [
    path('projects', ProjectApiView.as_view(), name='projects'),
    path('projects/<uuid:pk>', ProjectApiView.as_view(), name='project-detail'),
    path('account-codes', AccountCodeApiView.as_view(), name='account-codes'),
    path('account-codes/<uuid:pk>', AccountCodeApiView.as_view(), name='account-code-detail'),
    path('job-codes', JobCodeApiView.as_view(), name='job-codes'),
    path('job-codes/<uuid:pk>', JobCodeApiView.as_view(), name='job-code-detail'),
    path('asset-statuses', AssetStatusApiView.as_view(), name='asset-statuses'),
    path('asset-statuses/<uuid:pk>', AssetStatusApiView.as_view(), name='asset-status-detail'),
]