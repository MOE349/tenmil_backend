from django.contrib import admin
from django.urls import include, path

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

from configurations.system_start_checks import system_start_checks
from django.conf.urls.static import static
from django.conf import settings

from .views import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', ping),
    path("v1/api/tenants/tenant", TenantView.as_view()),
    path("v1/api/tenants/tenant/<str:pk>", TenantView.as_view()),
    path("v1/api/users/", include('users.platforms.api.urls')),
    path('v1/api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('v1/api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('v1/api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) 
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

system_start_checks()
