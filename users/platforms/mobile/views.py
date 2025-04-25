from users.platforms.base.views import *
from users.platforms.mobile.serializers import *


class UserMobileView(UserBaseView):
    serializer_class = UserMobileSerializer


