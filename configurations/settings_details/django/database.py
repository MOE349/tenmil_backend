from configurations.settings_details.env import env
from django.conf import settings

enviroment = "STAGE_" if settings.DEBUG else "PROD_"
# Database
import os
# import dj_database_url


CONN_HEALTH_CHECKS = True
DATABASES = {
    'default': {
        'ENGINE': "django_tenants.postgresql_backend",
        'NAME': env('POSTGRES_DB'),
        'USER': env('POSTGRES_USER'),
        'PASSWORD': env('POSTGRES_PASSWORD'),
        'HOST': env('POSTGRES_HOST'),
        'PORT': env('POSTGRES_PORT'),
    }
}
# DATABASES = {
#     'default': dj_database_url.config(
#         default=os.getenv("DATABASE_URL"),  # safe default if running locally
#         conn_max_age=600,
#         ssl_require=True
#     )
# }

# # Required for django-tenants to work
# DATABASES['default']['ENGINE'] = 'django_tenants.postgresql_backend'

    # 'default': {
    #     'ENGINE': env(f"{enviroment}DATABASE_ENGINE"),
    #     'NAME': env(f"{enviroment}DATABASE_NAME"),
    #     'USER': env(f"{enviroment}DATABASE_USER"),
    #     'PASSWORD': env(f"{enviroment}DATABASE_PASSWORD"),
    #     'HOST': env(f"{enviroment}DATABASE_HOST"),
    #     'PORT': env(f"{enviroment}DATABASE_PORT"),
    # }
# }
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