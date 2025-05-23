from django.urls import path
from tenant_users.platforms.dashboard.views import *


urlpatterns = [
path('TenantUser', TenantuserDashboardView.as_view(), name='Tenantuser'), 

]