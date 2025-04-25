BASE_APPS = [
    'whitenoise.runserver_nostatic',
    'django_tenants',
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
    "rest_framework_simplejwt.token_blacklist",

]
PROJECT_APPS = [
    'users.apps.UsersConfig',
    'core.apps.CoreConfig',
    'custom_commands.apps.CustomCommandsConfig',
]
TENANT_APPS = [
    'company.apps.CompanyConfig',
    'assets.apps.AssetsConfig',
    'financial_reports.apps.FinancialReportsConfig',
    'meter_readings.apps.MeterReadingsConfig',
    'work_orders.apps.WorkOrdersConfig',
]
