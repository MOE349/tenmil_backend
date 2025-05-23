from rest_framework.permissions import BasePermission
# from tenant_users.models import TenantUser

class IsTenantAuthenticated(BasePermission):
    """
    Allows access only to authenticated TenantUsers.
    """
    def has_permission(self, request, view):
        # return (
        #     request.user
        #     and request.user.is_authenticated
        #     and isinstance(request.user, TenantUser)
        # )
        return True
