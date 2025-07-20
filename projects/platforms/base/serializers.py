from configurations.base_features.serializers.base_serializer import BaseSerializer
from projects.models import *


class ProjectBaseSerializer(BaseSerializer):
    class Meta:
        model = Project
        fields = '__all__'


class AccountCodeBaseSerializer(BaseSerializer):
    class Meta:
        model = AccountCode
        fields = '__all__'


class JobCodeBaseSerializer(BaseSerializer):
    class Meta:
        model = JobCode
        fields = '__all__'


class AssetStatusBaseSerializer(BaseSerializer):
    class Meta:
        model = AssetStatus
        fields = '__all__'


