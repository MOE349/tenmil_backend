import traceback
from django.db import models
from ..exceptions.base_exceptions import LocalBaseException

class BaseManager(models.Manager):
    """
    Shared manager for all Tenmil models.
    Includes soft-delete filtering, FK-aware lookups, and DRF-friendly exceptions.
    """

    def model_field_exists(self, field: str) -> bool:
        try:
            self.model._meta.get_field(field)
            return True
        except Exception:
            return False

    def model_field_type(self, field: str) -> str:
        return self.model._meta.get_field(field).get_internal_type()

    def get_object_or_404(self, raise_exception=False, *args, **kwargs):
        data = None
        errors = []
        exception_type = None
        exception_kwargs = {}
        exception_debug = None
        status_code = 200

        if self.model_field_exists("is_deleted") and "is_deleted" not in kwargs:
            kwargs["is_deleted"] = False

        try:
            query_params = {}
            for field, value in kwargs.items():
                base_field = field.split("__")[0]
                field_type = self.model_field_type(base_field)
                if field_type == "ForeignKey":
                    query_params[f"{base_field}__id"] = value
                else:
                    query_params[field] = value

            data = self.get(*args, **query_params)

        except self.model.MultipleObjectsReturned:
            exception_type = "multiple_objects_returned"
            status_code = 409
            errors = f"Multiple {self.model._meta.object_name} objects found."
            exception_kwargs = {
                "count": self.filter(*args, **query_params).count(),
                "model": self.model._meta.object_name
            }

        except self.model.DoesNotExist:
            exception_type = "not_found"
            status_code = 404
            errors = f"{self.model._meta.object_name} not found."
            exception_kwargs = {"model": self.model._meta.object_name}

        except Exception as e:
            traceback.print_exc()
            exception_type = "internal_error"
            status_code = 500
            errors = "Unexpected error"
            exception_debug = str(e)

        if raise_exception:
            if exception_type:
                raise LocalBaseException(
                    exception_type=exception_type,
                    status_code=status_code,
                    kwargs=exception_kwargs,
                    debug_message=exception_debug,
                )
            return data
        else:
            return data, errors, status_code

    def not_deleted(self):
        """
        Return queryset excluding soft-deleted objects.
        """
        if self.model_field_exists("is_deleted"):
            return self.filter(is_deleted=False)
        return self.all()

    def active(self):
        """
        Return queryset for active objects (requires `is_active` field).
        """
        if self.model_field_exists("is_active"):
            return self.filter(is_active=True)
        return self.all()

    def active_not_deleted(self):
        """
        Combined filter: is_active=True and is_deleted=False.
        """
        qs = self.all()
        if self.model_field_exists("is_active"):
            qs = qs.filter(is_active=True)
        if self.model_field_exists("is_deleted"):
            qs = qs.filter(is_deleted=False)
        return qs

    def get_or_none(self, *args, **kwargs):
        """
        Returns an object or None if not found (safe fallback).
        """
        try:
            return self.get(*args, **kwargs)
        except self.model.DoesNotExist:
            return None
        except Exception:
            return None

    def create_or_update(self, lookup_fields: dict, defaults: dict = None):
        """
        Looks for existing object based on lookup_fields.
        If found, updates it. If not, creates new one.
        """
        defaults = defaults or {}
        instance = self.get_or_none(**lookup_fields)
        if instance:
            for key, value in defaults.items():
                setattr(instance, key, value)
            instance.save()
            return instance, False
        else:
            data = {**lookup_fields, **defaults}
            return self.create(**data), True
