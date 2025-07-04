from django.conf import settings

CORS_ALLOW_ALL_ORIGINS = settings.DEBUG  # True for dev, False for prod
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://*.localhost:3000",
    "http://127.0.0.1:3000",
    "https://alfrih.com",
    "https://*.alfrih.com",
    "https://*.lovable.app/assets"
]
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [origin.replace("http", "https") for origin in CORS_ALLOWED_ORIGINS if "localhost" not in origin]
