from vendors.platforms.base.views import *
from vendors.platforms.dashboard.serializers import *


class VendorDashboardView(VendorBaseView):
    serializer_class = VendorDashboardSerializer


class ContactPersonnelDashboardView(ContactPersonnelBaseView):
    serializer_class = ContactPersonnelDashboardSerializer


