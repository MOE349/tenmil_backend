import os
from configurations.settings_details.env import env, BASE_DIR
from configurations.settings_details.django.installed_apps import (
    BASE_APPS,
    PROJECT_APPS,
    THIRD_PARTY_APPS,
    TENANT_APPS,
    
)


# DEBUG = env.bool("DEBUG", True)
DEBUG = env("DEBUG")
enviroment = "STAGE_" if DEBUG else "PROD_"
# SECURITY WARNING: don't run with debug turned on in production!
SECRET_KEY = env(f"{enviroment}DJANGO_SECRET_KEY")

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "alfrih.com", ".alfrih.com", '.vercel.app']
ENVIROMENT = env(f"{enviroment}ENVIROMENT")

AUTH_USER_MODEL = 'users.User'


ROOT_URLCONF = 'configurations.urls'


# Application definition
SHARED_APPS = [*BASE_APPS,
               *PROJECT_APPS,
               *THIRD_PARTY_APPS]
INSTALLED_APPS = [
    *SHARED_APPS,
    *TENANT_APPS
]


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django_tenants.middleware.main.TenantMainMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, "frontend/dist/")
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'configurations.wsgi.app'
ASGI_APPLICATION = 'configurations.asgi.application'

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

#Authentication backends
AUTHENTICATION_BACKENDS = (
        'django.contrib.auth.backends.ModelBackend',
    )


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

APPEND_SLASH=False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

