from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings
from tenant_users.models import TenantUser

class TenantJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user_id = validated_token.get(api_settings.USER_ID_CLAIM)

        if user_id is None:
            return None

        try:
            return TenantUser.objects.get(id=user_id)
        except TenantUser.DoesNotExist:
            return None
