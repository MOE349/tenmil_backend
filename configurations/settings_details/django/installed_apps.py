BASE_APPS = [
    'django_tenants',
    'whitenoise.runserver_nostatic',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]
THIRD_PARTY_APPS = [
    'rest_framework',
    "corsheaders",
    'rest_framework_simplejwt',
    "django_extensions",
    "django_celery_beat",
    # "rest_framework_simplejwt.token_blacklist",

]
PROJECT_APPS = [
    'admin_users.apps.AdminUsersConfig',
    'core.apps.CoreConfig',
    'custom_commands.apps.CustomCommandsConfig',
]
TENANT_APPS = [
    'tenant_users.apps.TenantUsersConfig',
    'company.apps.CompanyConfig',
    'assets.apps.AssetsConfig',
    'financial_reports.apps.FinancialReportsConfig',
    'meter_readings.apps.MeterReadingsConfig',
    'work_orders.apps.WorkOrdersConfig',
    "fault_codes.apps.FaultCodesConfig",
    "pm_automation.apps.PmAutomationConfig",
    "projects.apps.ProjectsConfig",
    "asset_backlogs.apps.AssetBacklogsConfig",
]
