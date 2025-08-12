from django.urls import path
from components.platforms.api.views import *


urlpatterns = [
    path('component/', ComponentApiView.as_view(), name='component-list'),
    path('component/<uuid:pk>/', ComponentApiView.as_view(), name='component-detail'),
]