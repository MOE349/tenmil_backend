from django.urls import path
from tenant_users.platforms.mobile.views import *


urlpatterns = [
path('TenantUser', TenantuserMobileView.as_view(), name='Tenantuser'), 

]