from django.urls import path
from assets.platforms.api.views import *


urlpatterns = [
    path("assets/<str:pk>/move/", AssetMoveApiView.as_view(), name="assets-move"),
    path('assets', AssetApiView.as_view(), name='Assets'),
    path('equipments', EquipmentApiView.as_view(), name='Equipments'),
    path('equipments/<str:pk>', EquipmentApiView.as_view(), name='Equipment'),
    path('attachments', AttachmentApiView.as_view(), name='Attachments'),
    path('attachments/<str:pk>', AttachmentApiView.as_view(), name='Attachment'),
    path('equipment_category', EquipmentCategoryApiView.as_view(), name="Equipment Category"),
    path('equipment_category/<str:pk>', EquipmentCategoryApiView.as_view(), name="Equipment Category"),
    path('attachment_category', AttachmentCategoryApiView.as_view(), name="Attachment Category"),
    path('attachment_category/<str:pk>', AttachmentCategoryApiView.as_view(), name="Attachment Category"),

]
