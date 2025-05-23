from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from admin_users.platforms.base.serializers import *
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

class AdminLoginBaseView(TokenObtainPairView):
    serializer_class = AdminTokenObtainPairBaseSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(request, email=email, password=password)

        if not user:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        return self.format_response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "email": user.email,
            "name": user.name,
        }, [], 200)

class AdminRegisterBaseView(APIView):
    serializer_class = AdminRegisterBaseSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']
    authentication_classes = []

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "Admin registered successfully."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
