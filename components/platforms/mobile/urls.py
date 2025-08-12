from django.urls import path
from components.platforms.mobile.views import *


urlpatterns = [
path('component', ComponentMobileView.as_view(), name='Component'), 

]