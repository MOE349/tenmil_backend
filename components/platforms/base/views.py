from configurations.base_features.views.base_api_view import BaseAPIView
from configurations.base_features.exceptions.base_exceptions import LocalBaseException
from components.models import *
from components.platforms.base.serializers import *


class ComponentBaseView(BaseAPIView):
    serializer_class = ComponentBaseSerializer
    model_class = Component

    def handle_post_data(self, request):
        """Handle post data processing"""
        data = super().handle_post_data(request)
        return data
    
    def create(self, data, params, return_instance=False, *args, **kwargs):
        """Create a new component"""
        instance, response = super().create(data, params, return_instance=True, *args, **kwargs)
        return self.format_response(data=response, status_code=201)
    
    def update(self, data, params, pk, partial, *args, **kwargs):
        """Update an existing component"""
        response = super().update(data, params, pk, partial, *args, **kwargs)
        return self.format_response(data=response, status_code=200)
    
    def retrieve(self, pk, params, *args, **kwargs):
        """Retrieve a specific component"""
        response = super().retrieve(pk, params, *args, **kwargs)
        return self.format_response(data=response, status_code=200)
    
    def list(self, params, *args, **kwargs):
        """List all components"""
        response = super().list(params, *args, **kwargs)
        return self.format_response(data=response, status_code=200)
    
    def destroy(self, pk, params, *args, **kwargs):
        """Delete a component"""
        super().destroy(pk, params, *args, **kwargs)
        return self.format_response(data={"message": "Component deleted successfully"}, status_code=200)


