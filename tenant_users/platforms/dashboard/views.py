from tenant_users.platforms.base.views import *
from tenant_users.platforms.dashboard.serializers import *


class TenantuserDashboardView(TenantuserBaseView):
    serializer_class = TenantuserDashboardSerializer


