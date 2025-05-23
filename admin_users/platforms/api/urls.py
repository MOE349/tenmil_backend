from django.urls import path
from admin_users.platforms.api.views import *


urlpatterns = [
path('login', AdminLoginApiView.as_view(), name='admin_login'),
path('register', AdminRegisterApiView.as_view(), name='admin_register'),
# path('user'),

]