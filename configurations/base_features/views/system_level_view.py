from configurations.base_features.views.base_api_view import BaseAPIView
from configurations.base_features.exceptions.base_exceptions import LocalBaseException

class SystemLevelView(BaseAPIView):
    def update(self, data, params, pk, partial, return_instance=False, *args, **kwargs):
        instance = self.get_instance(pk)
        if instance.is_system_level:
            raise LocalBaseException(exception="System level maintenance type cannot be updated", status_code=400)
        return super().update(data, params, pk, partial, return_instance, *args, **kwargs)

    def destroy(self, request, pk, *args, **kwargs):
        params = self.get_request_params(request)
        params.pop('lang', 'en')
        instance = self.get_instance(pk)
        if instance.is_system_level:
            raise LocalBaseException(exception="System level maintenance type cannot be deleted", status_code=400)
        instance.delete()
        return self.format_response(data={}, status_code=204)