from django.urls import path, include
from django.contrib import admin

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

# from configurations.system_start_checks import system_start_checks
from configurations.views import *
from django.conf.urls.static import static
from django.conf import settings


api_urls = [
    path('dashboard', DashboardApiView.as_view(), name='dashboard'),
    path('users/', include('tenant_users.platforms.api.urls')),
    path('company/', include('company.platforms.api.urls')),
    path('assets/', include('assets.platforms.api.urls')),
    path('financial-reports/', include('financial_reports.platforms.api.urls')),
    path('meter-readings/', include('meter_readings.platforms.api.urls')),
    path('work-orders/', include('work_orders.platforms.api.urls')),
    # path('scheduled-maintenance/', include('scheduled_maintenance.platforms.api.urls')),
    path('fault-codes/', include('fault_codes.platforms.api.urls')),
    path('pm-automation/', include('pm_automation.platforms.api.urls')),
    path('projects/', include('projects.platforms.api.urls')),
]
# dashboard_urls = [
#     # path('users/', include('users.platforms.dashboard.urls')),
#     path('company/', include('company.platforms.dashboard.urls')),
#     path('assets/', include('assets.platforms.dashboard.urls')),
#     path('financial-reports/', include('financial_reports.platforms.dashboard.urls')),
#     path('meter-readings/', include('meter_readings.platforms.dashboard.urls')),
#     path('work-orders/', include('work_orders.platforms.dashboard.urls')),
#     path('scheduled-maintenance/', include('scheduled_maintenance.platforms.dashboard.urls')),
# ]

# mobile_urls = [
#     # path('users/', include('users.platforms.mobile.urls')),
#     path('company/', include('company.platforms.mobile.urls')),
#     path('assets/', include('assets.platforms.mobile.urls')),
#     path('financial-reports/', include('financial_reports.platforms.mobile.urls')),
#     path('meter-readings/', include('meter_readings.platforms.dashboard.urls')),
#     path('work-orders/', include('work_orders.platforms.mobile.urls')),
#     path('scheduled-maintenance/', include('scheduled_maintenance.platforms.mobile.urls')),
# ]
v1_urlpatterns = [
    path('api/', include(api_urls)),
 
    # path('dashboard/', include(dashboard_urls)),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('v1/', include(v1_urlpatterns)),    
    path('', index),
    path('v1/api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('v1/api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('v1/api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
# system_start_checks()