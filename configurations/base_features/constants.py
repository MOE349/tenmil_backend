from django.contrib.auth import get_user_model


# BASE
User = get_user_model()
SERVER_VERSION = "0.1.0"
STANDARD_GROUPS = ["super_admin", "admin",
                   "senior_support", "support", "analytics", "member"]
