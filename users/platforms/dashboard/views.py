from users.platforms.base.views import *
from users.platforms.dashboard.serializers import *


class UserDashboardView(UserBaseView):
    serializer_class = UserDashboardSerializer


