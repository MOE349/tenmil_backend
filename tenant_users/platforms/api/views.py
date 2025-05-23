from tenant_users.platforms.base.views import *
from tenant_users.platforms.api.serializers import *


class TenantLoginApiView(TenantLoginBaseView):
    serializer_class = TenantTokenObtainPairApiSerializer


class TenantRegisterApiView(TenantRegisterBaseView):
    serializer_class = TenantRegisterApiSerializer

class TenantUserApiView(TenantUserBaseView):
    serializer_class = TenantUserApiSerializer