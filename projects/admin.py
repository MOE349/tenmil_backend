from projects.models import *
from django.contrib import admin


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at', 'updated_at')
    search_fields = ('name',)
    list_filter = ('created_at', 'updated_at')
    ordering = ('name',)


@admin.register(AccountCode)
class AccountCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'project', 'created_at', 'updated_at')
    search_fields = ('name', 'project__name')
    list_filter = ('project', 'created_at', 'updated_at')
    ordering = ('project__name', 'name')


@admin.register(JobCode)
class JobCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'account_code', 'project', 'created_at', 'updated_at')
    search_fields = ('name', 'account_code__name', 'account_code__project__name')
    list_filter = ('account_code__project', 'account_code', 'created_at', 'updated_at')
    ordering = ('account_code__project__name', 'account_code__name', 'name')
    
    def project(self, obj):
        return obj.account_code.project.name
    project.short_description = 'Project'


@admin.register(AssetStatus)
class AssetStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'job_code', 'account_code', 'project', 'created_at', 'updated_at')
    search_fields = ('name', 'job_code__name', 'job_code__account_code__name', 'job_code__account_code__project__name')
    list_filter = ('job_code__account_code__project', 'job_code__account_code', 'job_code', 'created_at', 'updated_at')
    ordering = ('job_code__account_code__project__name', 'job_code__account_code__name', 'job_code__name', 'name')
    
    def account_code(self, obj):
        return obj.job_code.account_code.name
    account_code.short_description = 'Account Code'
    
    def project(self, obj):
        return obj.job_code.account_code.project.name
    project.short_description = 'Project'
