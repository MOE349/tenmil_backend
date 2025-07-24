from django.urls import path
from asset_backlogs.platforms.mobile.views import *


urlpatterns = [
path('asset_backlog', AssetBacklogMobileView.as_view(), name='AssetBacklog'), 

]