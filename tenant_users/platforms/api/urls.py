from django.urls import path
from tenant_users.platforms.api.views import *


urlpatterns = [
path('login', TenantLoginApiView.as_view(), name='tenant_login'), 
path('register', TenantRegisterApiView.as_view(), name='tenant_register'), 
path('user', TenantUserApiView.as_view(), name='tenant_user'),

]