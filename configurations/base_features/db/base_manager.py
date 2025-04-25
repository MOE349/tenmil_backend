from django.db import models
from ..exceptions.base_exceptions import LocalBaseException


class BaseManager(models.Manager):
    def model_field_exists(self, field):
        try:
            self.model._meta.get_field(field)
            return True
        except:
            return False

    def get_object_or_404(self, raise_exception=False, *args, **kwargs):
        """
        Get an object or return a 404 not found response.
        """
        data = []
        errors = []
        has_exceptions = False
        exception = None
        exception_kwargs = None
        status_code = 200

        try:
            if self.model_field_exists('is_deleted') and 'is_deleted' not in kwargs:
                kwargs["is_deleted"] = False
            data = self.get(*args, **kwargs)
        except self.model.MultipleObjectsReturned:
            has_exceptions = True
            errors = (f"{self.filter(*args, **kwargs).count()} {self.model._meta.object_name.lower()} \
                 instances found.")
            exception_type = "multiple_objects_returned"
            status_code = 409
            exception_kwargs = {"count": self.filter(
                *args, **kwargs).count(), "model": self.model._meta.object_name.lower()}
        except self.model.DoesNotExist:
            has_exceptions = True
            errors = f"{self.model._meta.object_name.lower()} not found."
            exception_type = "not_found"
            status_code = 404
            exception_kwargs = {"model": self.model._meta.object_name.lower()}
        except Exception as e:
            has_exceptions = True
            exception_type = ""
            errors = str(e)
            status_code = 500
            exception = {"error": str(e)}

        if raise_exception:
            if has_exceptions:
                raise LocalBaseException(
                    exception_type=exception_type,
                    status_code=status_code,
                    exception=exception,
                    kwargs=exception_kwargs
                )
            return data
        else:
            return data, errors, status_code
