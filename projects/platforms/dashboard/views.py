from projects.platforms.base.views import *
from projects.platforms.dashboard.serializers import *


class ProjectDashboardView(ProjectBaseView):
    serializer_class = ProjectDashboardSerializer


class AccountCodeDashboardView(AccountCodeBaseView):
    serializer_class = AccountCodeDashboardSerializer


class JobCodeDashboardView(JobCodeBaseView):
    serializer_class = JobCodeDashboardSerializer


class AssetStatusDashboardView(AssetStatusBaseView):
    serializer_class = AssetStatusDashboardSerializer


