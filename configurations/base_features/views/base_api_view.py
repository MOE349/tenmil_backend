from rest_framework.views import APIView
from assets.models import Attachment, Equipment
from assets.services import get_assets_by_gfk, get_content_type_and_asset_id
from configurations import settings
from configurations.base_features.exceptions.base_exceptions import LocalBaseException
from configurations.base_features.helpers.text_helpers import snake_to_title
from configurations.base_features.views.base_exception_handler import BaseExceptionHandlerMixin
from configurations.base_features.views.base_response import ResponseFormatterMixin
from tenant_users.auth_backend import TenantUserAuthBackend
from tenant_users.auth_jwt import TenantJWTAuthentication
from tenant_users.permissions import IsTenantAuthenticated
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import ForeignKey, ManyToManyField, QuerySet

class BaseAPIView(TenantUserAuthBackend, BaseExceptionHandlerMixin, APIView, ResponseFormatterMixin):
    """
        an abstract class for all api views

        by default it accepts:
            all http methods: could be modified by adding http_method_names to your class
            all user roles: could be modified by adding allowed_roles to your class, please note that "super-admin", "admin" roles will be addeded automatically,
                            unless allowed_roles has "super-admin" then "admin won't be added later on.

        by default only authenticated users can access the api, to change this override get, post, put or delete as needed by
            calling super() and allow_unauthenticated_user=True, eg: to allow unauthenticated users to access get:

                def get(self, request, pk=None, params=None, *args, **kwargs):
                    super().get(request, pk=None, params=None,
                          allow_unauthenticated_user=True, *args, **kwargs)

            it's not recommended to override get, post, put or delete, as they act like a middleware to handle exceptions and authorize users,
            but you can override list, retreive, create, update and destroy as needed safely.

        model_class and serializer_class are required to be set in your class
    """
    model_class = None
    serializer_class = None
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]
    # authentication_classes = [AuthMixin]
    permission_classes = [IsTenantAuthenticated]
    authentication_classes = [TenantJWTAuthentication]
    # ['*'] to allow all roles or specify roles like ['admin', 'support'] from STANDARD_GROUPS
    allowed_roles = ['*']  # "super-admin" and "admin" are always allowed

    def get_request_user(self, request):
        """Get the request user, if not authenticated raise BaseException"""
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            raise LocalBaseException("not_authenticated", status_code=401)
        return user

    def get_user_role(self, user):
        """Get the user role"""
        user_roles = [role.name for role in user.groups.all()]
        return user_roles

    def authorize_user(self, request):
        return self.authenticate(request)
        # """Authorize the user based on the allowed roles"""
        # # add "super-admin" and "admin" to allowed roles
        # if "super-admin" not in self.allowed_roles:
        #     allowed_roles = ["super-admin", "admin", *self.allowed_roles]
        # else:
        #     allowed_roles = self.allowed_roles

        # user = self.get_request_user(request)
        # user_role = self.get_user_role(user)
        # if "*" not in allowed_roles and not set(user_role) & set(allowed_roles):
        #     raise LocalBaseException(exception_type="not_authorized", status_code=401)
        # return user, user_role


    def get_field_properities(self, data=None):
        """Get the field properties"""
        fields = []
        model_fields = [
            field.name for field in self.model_class._meta.get_fields()]
        keys = data.keys() if data else model_fields
        for field in keys:
            slug = field
            type_ = self.model_class._meta.get_field(
                field).get_internal_type() if field in model_fields else "ForeignKey"
            name = snake_to_title(field)
            fields.append({"slug": slug, "name": name, "type": type_})
        sorted_fields = fields.copy()
        for field in fields:
            if field['slug'] == 'id':
                sorted_fields.remove(field)
                sorted_fields.insert(0, field)
            elif field['slug'] == 'description':
                sorted_fields.remove(field)
                sorted_fields.insert(-1, field)
            elif field['type'] in ['DateTimeField', 'DateField', 'TextField', 'BooleanField']:
                sorted_fields.remove(field)
                if sorted_fields[-1]['slug'] == 'description':
                    sorted_fields.insert(-2, field)
                elif sorted_fields[-2]['slug'] == 'description':
                    sorted_fields.insert(-3, field)
                else:
                    sorted_fields.insert(-1, field)
            else:
                sorted_fields.remove(field)
                sorted_fields.insert(1, field)

        return sorted_fields
    
    def modify_params(self, old_params):
        params = {}
        for field in old_params.keys():
            field_type =self.model_class._meta.get_field(field.split('__')[0]).get_internal_type()
            if field_type == 'ForeignKey':
                params[f"{field.split('__')[0]}__id"] = old_params[field]
            else:
                params[field] = old_params[field]
        return params
    
    def get_queryset(self, params=None, ordering=None):
        """Get the queryset based on the given params"""
        params = self.modify_params(params)
        if params is None:
            params = {}
        if "Q" in params:
            q_params = params.pop("Q")
        else:
            q_params = []
        if hasattr(self.model_class, "asset") and "asset" in params:
            asset_id = params.pop('asset')
            instances = get_assets_by_gfk(self.model_class, asset_id, *q_params, **params)
        else:
            instances = self.model_class.objects.filter(*q_params, **params)
        if ordering:
            instances = instances.order_by(ordering)
        else:
            instances = instances.order_by("-created_at")
        return instances

    def get_instance(self, pk=None, params=None):
        """Get the instance based on the given params"""
        if params is None:
            params = {}
        if pk:
            params["id"] = pk
        if hasattr(self.model_class, "asset") and "asset" in params:
            asset_id = params.pop('asset')
            instance = get_assets_by_gfk(self.model_class, asset_id, **params).first()
        else:
            instance = self.model_class.objects.get_object_or_404(
            raise_exception=True, **params)
        return instance

    def get_serialized_objects(self, instance, many=False):
        """Get the serialized objects based on the given instance"""
        serializer = self.serializer_class(instance, many=many)
        return serializer.data

    def get_request_params(self, request):
        """
        Converts query params into Django filter kwargs,
        skipping FK, M2M, and GFK fields from being wrapped in `__icontains`.
        """
        model_fields = {f.name: f for f in self.model_class._meta.get_fields()}
        gfk_field_names = {
            f.name for f in self.model_class._meta.private_fields
            if isinstance(f, GenericForeignKey)
        }

        params = {}
        for key, value in request.query_params.items():
            if key in ['_end', '_start']:
                continue

            field_name = key.split("__")[0]  # e.g., 'category__name' → 'category'
            field = model_fields.get(field_name)

            is_gfk = key in gfk_field_names
            is_fk = isinstance(field, ForeignKey) if field else False
            is_m2m = isinstance(field, ManyToManyField) if field else False

            if is_fk or is_m2m or is_gfk:
                params[key] = value
            else:
                params[f"{key}__icontains"] = value

        return params

    def clear_paginations_params(self, params):
        params.pop("page", None)
        params.pop("pageSize", None)
        return params

    def get(self, request, pk=None, params=None, allow_unauthenticated_user=False, *args, **kwargs):
        """
            :params: pk - primary key of the object, if provided call retreive() else call list(), override those 2 methods as needed
            :params: allow_unauthenticated_user - allow unauthenticated user to access the object
            :params: params - params to filter the object, could be added by overriding the method then calling super().get(), eg:
                def get(self, request, pk=None, params=None, *args, **kwargs):
                    # pk is a user pk and we are in get method for user_profile
                    user = User.objects.get(pk=pk)
                    params = {'user': user}
                    super().get(request, pk=None, params=params,
                          allow_unauthenticated_user=True, *args, **kwargs)
        """
        try:
            # if not allow_unauthenticated_user:
            #     self.authorize_user(request)
            if params is None:
                params = self.get_request_params(request)
            params = self.clear_paginations_params(params)
            if settings.DEBUG:
                print(f"[{self.__class__.__name__}] GET pk: {pk}")
            if pk:
                return self.retrieve(pk, params,  *args, **kwargs)
            else:
                return self.list(params,  *args, **kwargs)
        except Exception as e:
            return self.handle_exception(e)

    def retrieve(self, pk, params, *args, **kwargs):
        """Get single serialized object"""
        user_lang = params.pop('lang', 'en')
        if "ordering" in params:
            params.pop('ordering')
        if pk == "0":
            fields = self.get_field_properities()
            return self.format_response(data=[], status_code=200, fields=fields)
        instance_object = self.get_instance(pk, params)
        serialized_data = self.get_serialized_objects(instance_object)
        fields = self.get_field_properities(serialized_data)
        return self.format_response(data=serialized_data, status_code=200, fields=fields)

    def list(self, params, *args, **kwargs):
        """Get list of serialized objects"""
        ordering_by = None
        if "ordering" in params:
            ordering_by = params.pop('ordering')
        user_lang = params.pop('lang', 'en')
        instance_objects = self.get_queryset(params=params, ordering=ordering_by)
        serialized_data = self.get_serialized_objects(
            instance_objects, many=True)
        return self.format_response(data=serialized_data, status_code=200)
    
    def handle_post_params(self, request, params, allow_unauthenticated_user=False):
        if not allow_unauthenticated_user:
            params['user'] = request.user
        params['lang'] = 'en'
        return params
    
    def handle_post_data(self, request):
        data = request.data.copy()
        if "asset" in data:
            asset = data.pop("asset")
            data['content_type'], data['object_id'] = get_content_type_and_asset_id(asset)
        return data
    
    def post(self, request, allow_unauthenticated_user=False, *args, **kwargs):
        """
            :param allow_unauthenticated_user: Allow unauthenticated user to access this endpoint
            calls create method, override create() as needed
        """
        try:
            # if not allow_unauthenticated_user:
            #     self.authorize_user(request)
            data = self.handle_post_data(request)
            params = self.get_request_params(request)
            params = self.handle_post_params(request, params, allow_unauthenticated_user)
            return self.create(data, params, *args, **kwargs)
        except Exception as e:
            return self.handle_exception(e)

    def create(self, data, params, return_instance=False, *args, **kwargs):       
        """Create new object"""
        user_lang = params.pop('lang', 'en')
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        if return_instance:
            return instance, serializer.data
        return self.format_response(data=serializer.data, status_code=201)

    def handle_update_data(self, request):
        data = request.data.copy()
        if "asset" in data:
            asset = data.pop("asset")
            data['content_type'], data['object_id'] = get_content_type_and_asset_id(asset)
        return data
    
    def put(self, request, pk, partial=False,  allow_unauthenticated_user=False, *args, **kwargs):
        """
            :param pk : Primary key of the object to be updated
            :param partial: Whether to update all fields or only the fields provided in the request
            :param allow_unauthenticated_user: Allow unauthenticated user to access this endpoint
            calls update method, override update() as needed"""
        try:
            # if not allow_unauthenticated_user:
            #     self.authorize_user(request)
            data = self.handle_update_data(request)
            params = self.get_request_params(request)
            params = self.handle_post_params(request, params, allow_unauthenticated_user)
            return self.update(data, params, pk, partial, *args, **kwargs)
        except Exception as e:
            return self.handle_exception(e)

    def update(self, data, params,  pk, partial, return_instance=False, * args, **kwargs):
        """Update an object"""
        user_lang = params.pop('lang', 'en')
        instance = self.get_instance(pk)
        serializer = self.serializer_class(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response = serializer.data
        if return_instance:
            return instance, response
        return self.format_response(data=serializer.data, status_code=200)

    def patch(self, request, pk, *args, **kwargs):
        """
        Update an object partially
        it calls put method and from there calls update method
        override update method as needed
        """
        return self.put(request, pk, partial=True, *args, **kwargs)

    def delete(self, request, pk, allow_unauthenticated_user=False, *args, **kwargs):
        """
        it calls destroy method, override destroy as needed
        """
        try:
            # if not allow_unauthenticated_user:
            #     self.authorize_user(request)
            return self.destroy(request, pk, *args, **kwargs)
        except Exception as e:
            return self.handle_exception(e)

    def destroy(self, request, pk, *args, **kwargs):
        """Delete an object"""
        params = self.get_request_params(request)
        user_lang = params.pop('lang', 'en')
        instance = self.get_instance(pk)
        instance.delete()
        return self.format_response(data={}, status_code=204)
