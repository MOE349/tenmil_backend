from admin_users.platforms.base.views import *
from admin_users.platforms.dashboard.serializers import *


class AdminuserDashboardView(AdminuserBaseView):
    serializer_class = AdminuserDashboardSerializer


