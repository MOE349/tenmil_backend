import traceback
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from configurations.base_features.views.auth_mixin import AuthMixin
from configurations.base_features.views.base_api_view import BaseAPIView
from tenant_users.auth_backend import TenantUserAuthBackend
from rest_framework_simplejwt.tokens import RefreshToken
from tenant_users.platforms.base.serializers import *
from rest_framework.views import APIView



class TenantLoginBaseView(TokenObtainPairView):
    serializer_class = TenantTokenObtainPairBaseSerializer
    permission_classes = [AllowAny]
    authentication_classes=[]
    
    def post(self, request, *args, **kwargs):
        try:
            email = request.data.get('email')
            password = request.data.get('password')
            print(email, password)
            user = TenantUserAuthBackend().authenticate(request, email=email, password=password)

            if not user:
                return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

            refresh = RefreshToken.for_user(user)
            response ={
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "email": user.email,
                "name": user.name,
                "tenant_id": user.tenant_id
            }
            print("login response: ", response)
            return Response(response, status=status.HTTP_200_OK)
        except Exception as e:
            traceback.print_exc()
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TenantRegisterBaseView(APIView):
    serializer_class = TenantRegisterBaseSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']
    authentication_classes = []

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request':request})
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "Tenant user registered successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class TenantUserBaseView(BaseAPIView):
    model_class = TenantUser
    serializer_class = TenantUserBaseSerializer
    http_method_names = ['get']

    # def get(self, request):
    #     user = request.user
    #     if user.is_anonymous:
    #         return self.format_response({"user is not authenticated"}, [], 401)
    #     serializer = self.serializer_class(user)
    #     return self.format_response(serializer.data, [], 200)