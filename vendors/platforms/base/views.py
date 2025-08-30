from configurations.base_features.views.base_api_view import BaseAPIView
from vendors.models import *
from vendors.platforms.base.serializers import *


class VendorBaseView(BaseAPIView):
    serializer_class = VendorBaseSerializer
    model_class = Vendor


class ContactPersonnelBaseView(BaseAPIView):
    serializer_class = ContactPersonnelBaseSerializer
    model_class = ContactPersonnel


