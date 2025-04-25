from django.urls import path
from users.platforms.api.views import *


urlpatterns = [
path('user', UserApiView.as_view(), name='User'), 
path('login', LoginApiView.as_view(), name='login'),
path('register', RegisterApiView.as_view(), name='register'),

]