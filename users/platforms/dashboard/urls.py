from django.urls import path
from users.platforms.dashboard.views import *


urlpatterns = [
path('User', UserDashboardView.as_view(), name='User'), 

]