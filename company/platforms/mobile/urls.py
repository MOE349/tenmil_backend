from django.urls import path
from company.platforms.mobile.views import *


urlpatterns = [
path('site', SiteMobileView.as_view(), name='Site'), 
path('location', LocationMobileView.as_view(), name='Location'), 

]