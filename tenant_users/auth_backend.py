from tenant_users.models import TenantUser

class TenantUserAuthBackend:
    def authenticate(self, request, email=None, password=None, **kwargs):
        tenant = getattr(request, 'tenant', None)
        if not tenant:
            return None
        try:
            user = TenantUser.objects.get(email=email, tenant=tenant)
            if user.check_password(password):
                return user
        except TenantUser.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return TenantUser.objects.get(pk=user_id)
        except TenantUser.DoesNotExist:
            return None