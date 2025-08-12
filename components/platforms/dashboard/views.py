from components.platforms.base.views import *
from components.platforms.dashboard.serializers import *


class ComponentDashboardView(ComponentBaseView):
    serializer_class = ComponentDashboardSerializer


