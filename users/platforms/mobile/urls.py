from django.urls import path
from users.platforms.mobile.views import *


urlpatterns = [
path('User', UserMobileView.as_view(), name='User'), 

]