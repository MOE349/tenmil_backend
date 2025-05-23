from admin_users.platforms.base.views import *
from admin_users.platforms.mobile.serializers import *


class AdminuserMobileView(AdminuserBaseView):
    serializer_class = AdminuserMobileSerializer


