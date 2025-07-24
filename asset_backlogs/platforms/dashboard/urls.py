from django.urls import path
from asset_backlogs.platforms.dashboard.views import *


urlpatterns = [
path('asset_backlog', AssetBacklogDashboardView.as_view(), name='AssetBacklog'), 

]