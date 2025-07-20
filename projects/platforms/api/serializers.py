from projects.platforms.base.serializers import *


class ProjectApiSerializer(ProjectBaseSerializer):
    class Meta(ProjectBaseSerializer.Meta):
        fields = ['id', 'name', 'created_at', 'updated_at']


class AccountCodeApiSerializer(AccountCodeBaseSerializer):
    project = ProjectApiSerializer(read_only=True)
    
    class Meta(AccountCodeBaseSerializer.Meta):
        fields = ['id', 'name', 'project', 'created_at', 'updated_at']


class JobCodeApiSerializer(JobCodeBaseSerializer):
    account_code = AccountCodeApiSerializer(read_only=True)
    
    class Meta(JobCodeBaseSerializer.Meta):
        fields = ['id', 'name', 'account_code', 'created_at', 'updated_at']


class AssetStatusApiSerializer(AssetStatusBaseSerializer):
    job_code = JobCodeApiSerializer(read_only=True)
    
    class Meta(AssetStatusBaseSerializer.Meta):
        fields = ['id', 'name', 'job_code', 'created_at', 'updated_at']


