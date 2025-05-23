from admin_users.platforms.base.views import *
from admin_users.platforms.api.serializers import *
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


class AdminLoginApiView(AdminLoginBaseView):
    serializer_class = AdminTokenObtainPairApiSerializer

@method_decorator(csrf_exempt, name='dispatch')
class AdminRegisterApiView(AdminRegisterBaseView):
    serializer_class = AdminRegisterApiSerializer

