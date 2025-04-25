
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from configurations.base_features.views.base_api_view import BaseAPIView

from users.models import *
from users.platforms.base.serializers import *


class UserBaseView(BaseAPIView):
    serializer_class = UserBaseSerializer
    model_class = User


class LoginBaseView(UserBaseView):
    serializer_class = LoginBaseSerializer
    model_class = User
    http_method_names = ["post"]
    authentication_classes=[]

    def post(self, request, allow_unauthenticated_user=True, *args, **kwargs):
        try:
            data = request.data.copy()
            password = data.get('password', None)
            email = data.get('email', None)
            serializer = self.serializer_class(data=data)
            serializer.is_valid(raise_exception=True)
            user = authenticate(username=email, password=password)

            if user is not None:
                login(request, user)
            else:
                # Return an 'invalid login' error message.
                raise LocalBaseException(exception="Can't login user", status_code=403)

            old_tokens = OutstandingToken.objects.filter(user=user)
            for token in old_tokens:
                token.delete()
            refresh = RefreshToken.for_user(user)
            
            response =  {
                'user':UserBaseSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }

            return self.format_response(response, status_code=200)
        except Exception as e:
            return self.handle_exception(e)

class RegisterBaseView(UserBaseView):
    serializer_class = RegisterBaseSerializer
    http_method_names = ["post"]
    authentication_classes=[]

    def post(self, request, allow_unauthenticated_user=True, *args, **kwargs):
        email = request.data.get('email', None)
        password = request.data.get('password', None)
        user = self.model_class.objects.create_user(**request.data)
        user.save()
        serializer = LoginBaseSerializer(user)
        user = authenticate(request=request, username=email, password=password)
        if user is not None:
            login(request, user)
        else:
            # Return an 'invalid login' error message.
            raise LocalBaseException(exception="Can't login user", status_code=403)

        refresh = RefreshToken.for_user(user)

        response =  {
            'user':UserBaseSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        return self.format_response(response, status_code=201)
    