from users.platforms.base.views import *
from users.platforms.api.serializers import *


class UserApiView(UserBaseView):
    serializer_class = UserApiSerializer


class LoginApiView(LoginBaseView):
    serializer_class = LoginApiSerializer

class RegisterApiView(RegisterBaseView):
    serializer_class = RegisterApiSerializer