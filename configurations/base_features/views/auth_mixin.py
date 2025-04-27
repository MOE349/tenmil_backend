# import traceback
import traceback
from rest_framework.authentication import BaseAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from configurations.base_features.constants import User
from configurations.base_features.error_translation import ERRORS
from configurations.base_features.exceptions.base_exceptions import LocalBaseException


class AuthMixin(BaseAuthentication):
    

    def authenticate(self, request):
        user_lang = 'en'
        not_authenticated_error = ERRORS['not_authenticated'][user_lang]
        not_found_error = ERRORS['not_found'][user_lang]
        try:            
            authenticator = JWTAuthentication()
            authentication  = authenticator.authenticate(request)
            if not authentication:
                raise LocalBaseException(not_authenticated_error, 401)
            user, token = authentication
            return user, token
        except (ValueError, KeyError, User.DoesNotExist) as e:
            traceback.print_exc()
            raise LocalBaseException(not_authenticated_error, 401)

    def get_user(self, request):
        # This is called by DRF to get the user from the request
        user = getattr(request, 'user', None)
        if user is not None:
            return user
