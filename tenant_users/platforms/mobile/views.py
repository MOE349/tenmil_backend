from tenant_users.platforms.base.views import *
from tenant_users.platforms.mobile.serializers import *


class TenantuserMobileView(TenantuserBaseView):
    serializer_class = TenantuserMobileSerializer


