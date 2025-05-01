from datetime import timedelta

from django.conf import settings


REST_FRAMEWORK = {
    # 'DEFAULT_AUTHENTICATION_CLASSES': (
    #     'rest_framework_simplejwt.authentication.JWTStatelessUserAuthentication',
    # ),
    # 'AUTH_TOKEN_CLASSES ':(
    #     'rest_framework_simplejwt.tokens.SlidingToken',
    # )
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=10),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=100),
    "UPDATE_LAST_LOGIN": True,
}