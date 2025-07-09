import os
from configurations.settings_details.env import BASE_DIR, environ

# Take environment variables from .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# import third party apps settings
from configurations.settings_details.third_party.celery_config import *  # noqa
from configurations.settings_details.third_party.cors_headers_config import *  # noqa
from configurations.settings_details.third_party.tenants import *  # noqa
from configurations.settings_details.third_party.rest_framework import *  # noqa

# import base django settings
from configurations.settings_details.django.project_data import *  # noqa
from configurations.settings_details.django.database import *  # noqa
from configurations.settings_details.django.base import *  # noqa


