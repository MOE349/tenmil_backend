from django.urls import path
from assets.platforms.mobile.views import *


urlpatterns = [
path('equipment', EquipmentMobileView.as_view(), name='Equipment'), 
path('attachment', AttachmentMobileView.as_view(), name='Attachment'), 

]