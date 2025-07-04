from configurations.settings_details.env import env
from django.conf import settings
import dj_database_url

enviroment = "STAGE_" if settings.DEBUG else "PROD_"
# Database
DATABASES = {
    'default': dj_database_url.config(conn_max_age=600, ssl_require=True)
    # 'default': {
    #     'ENGINE': env(f"{enviroment}DATABASE_ENGINE"),
    #     'NAME': env(f"{enviroment}DATABASE_NAME"),
    #     'USER': env(f"{enviroment}DATABASE_USER"),
    #     'PASSWORD': env(f"{enviroment}DATABASE_PASSWORD"),
    #     'HOST': env(f"{enviroment}DATABASE_HOST"),
    #     'PORT': env(f"{enviroment}DATABASE_PORT"),
    # }
}
# DATABASES = {
#     'default': {
#         'ENGINE': "django_tenants.postgresql_backend",
#         'NAME': "neondb",
#         'USER': "neondb_owner",
#         'PASSWORD': "npg_jC7N1wlMJaLY",
#         'HOST': "ep-still-field-a5zkks85-pooler.us-east-2.aws.neon.tech",
#         'PORT': "5433",
#     }
# }
DATABASE_ROUTERS = ['django_tenants.routers.TenantSyncRouter']

PUBLIC_SCHEMA_URLCONF = "configurations.urls"

TENANT_MODEL = "core.Client" # app.Model
TENANT_DOMAIN_MODEL = "core.Domain"  # app.Model