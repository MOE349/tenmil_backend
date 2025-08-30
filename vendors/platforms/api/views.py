from vendors.platforms.base.views import *
from vendors.platforms.api.serializers import *


class VendorApiView(VendorBaseView):
    serializer_class = VendorApiSerializer


class ContactPersonnelApiView(ContactPersonnelBaseView):
    serializer_class = ContactPersonnelApiSerializer


