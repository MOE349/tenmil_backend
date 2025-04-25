from django.urls import path
from assets.platforms.dashboard.views import *


urlpatterns = [
path('equipment', EquipmentDashboardView.as_view(), name='Equipment'), 
path('attachment', AttachmentDashboardView.as_view(), name='Attachment'), 

]