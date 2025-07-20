from configurations.base_features.views.base_api_view import BaseAPIView
from projects.models import *
from projects.platforms.base.serializers import *


class ProjectBaseView(BaseAPIView):
    serializer_class = ProjectBaseSerializer
    model_class = Project


class AccountCodeBaseView(BaseAPIView):
    serializer_class = AccountCodeBaseSerializer
    model_class = AccountCode


class JobCodeBaseView(BaseAPIView):
    serializer_class = JobCodeBaseSerializer
    model_class = JobCode


class AssetStatusBaseView(BaseAPIView):
    serializer_class = AssetStatusBaseSerializer
    model_class = AssetStatus


