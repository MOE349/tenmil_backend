from django.urls import path
from assets.platforms.api.views import *


urlpatterns = [
    path('equipments', EquipmentApiView.as_view(), name='Equipments'),
    path('equipments/<str:pk>', EquipmentApiView.as_view(), name='Equipment'),
    path('attachments', AttachmentApiView.as_view(), name='Attachments'),
    path('attachments/<str:pk>', AttachmentApiView.as_view(), name='Attachment'),
    path('equipment_category', EquipmentCategoryApiView.as_view(), name="Equipment Category"),
    path('equipment_category/<str:pk>', EquipmentCategoryApiView.as_view(), name="Equipment Category"),

]
