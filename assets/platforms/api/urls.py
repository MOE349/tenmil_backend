from django.urls import path
from assets.platforms.api.views import *


urlpatterns = [
    path("movement-log", AssetMoveApiView.as_view(), name="assets-move"),
    path('assets', AssetApiView.as_view(), name='Assets'),
    path('assets/<str:pk>', AssetApiView.as_view(), name='Asset details'),
    path('equipments', EquipmentApiView.as_view(), name='Equipments'),
    path('equipments/<str:pk>', EquipmentApiView.as_view(), name='Equipment'),
    path('attachments', AttachmentApiView.as_view(), name='Attachments'),
    path('attachments/<str:pk>', AttachmentApiView.as_view(), name='Attachment'),
    path('equipment_category', EquipmentCategoryApiView.as_view(), name="Equipment Category"),
    path('equipment_category/<str:pk>', EquipmentCategoryApiView.as_view(), name="Equipment Category"),
    path('attachment_category', AttachmentCategoryApiView.as_view(), name="Attachment Category"),
    path('attachment_category/<str:pk>', AttachmentCategoryApiView.as_view(), name="Attachment Category"),
    path('equipment_weight_class', EquipmentWeightClassApiView.as_view(), name="Equipment Weight Class"),
    path('equipment_weight_class/<str:pk>', EquipmentWeightClassApiView.as_view(), name="Equipment Weight Class"),

]
