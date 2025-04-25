from django.urls import path
from company.platforms.api.views import *


urlpatterns = [
path('site', SiteApiView.as_view(), name='Site'), 
path('site/<str:pk>', SiteApiView.as_view(), name='Site Details'), 
path('location', LocationApiView.as_view(), name='Location'), 
path('location/<str:pk>', LocationApiView.as_view(), name='Location Details'), 

]