from django.urls import path
from components.platforms.dashboard.views import *


urlpatterns = [
path('component', ComponentDashboardView.as_view(), name='Component'), 

]