from django.urls import path
from admin_users.platforms.dashboard.views import *


urlpatterns = [
path('AdminUser', AdminuserDashboardView.as_view(), name='Adminuser'), 

]