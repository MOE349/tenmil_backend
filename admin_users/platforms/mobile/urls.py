from django.urls import path
from admin_users.platforms.mobile.views import *


urlpatterns = [
path('AdminUser', AdminuserMobileView.as_view(), name='Adminuser'), 

]