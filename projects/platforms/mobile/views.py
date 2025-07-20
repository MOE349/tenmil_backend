from projects.platforms.base.views import *
from projects.platforms.mobile.serializers import *


class ProjectMobileView(ProjectBaseView):
    serializer_class = ProjectMobileSerializer


class AccountCodeMobileView(AccountCodeBaseView):
    serializer_class = AccountCodeMobileSerializer


class JobCodeMobileView(JobCodeBaseView):
    serializer_class = JobCodeMobileSerializer


class AssetStatusMobileView(AssetStatusBaseView):
    serializer_class = AssetStatusMobileSerializer


