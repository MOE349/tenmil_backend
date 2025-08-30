from vendors.platforms.base.views import *
from vendors.platforms.mobile.serializers import *


class VendorMobileView(VendorBaseView):
    serializer_class = VendorMobileSerializer


class ContactPersonnelMobileView(ContactPersonnelBaseView):
    serializer_class = ContactPersonnelMobileSerializer


