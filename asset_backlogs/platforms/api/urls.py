from django.urls import path
from asset_backlogs.platforms.api.views import *


urlpatterns = [
path('asset_backlog', AssetBacklogApiView.as_view(), name='AssetBacklog'), 
path('asset_backlog/<int:pk>/', AssetBacklogApiView.as_view(), name='AssetBacklog'), 

]