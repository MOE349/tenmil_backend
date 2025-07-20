from projects.platforms.base.views import *
from projects.platforms.api.serializers import *


class ProjectApiView(ProjectBaseView):
    serializer_class = ProjectApiSerializer


class AccountCodeApiView(AccountCodeBaseView):
    serializer_class = AccountCodeApiSerializer


class JobCodeApiView(JobCodeBaseView):
    serializer_class = JobCodeApiSerializer


class AssetStatusApiView(AssetStatusBaseView):
    serializer_class = AssetStatusApiSerializer


