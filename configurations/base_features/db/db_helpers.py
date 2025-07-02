from django.contrib.contenttypes.models import ContentType
from assets.models import *
from typing import Union, Type
from django.db.models import Model
from django.db.models.manager import BaseManager

from configurations.base_features.exceptions.base_exceptions import LocalBaseException

def get_object_by_content_type_and_id(content_type_id: int, object_id: str) -> Model:
    """
    Resolves and returns an object given a content_type ID and object ID.
    Raises LocalBaseException if invalid or not found.
    """
    try:
        content_type = ContentType.objects.get(pk=content_type_id)
    except ContentType.DoesNotExist:
        raise LocalBaseException("Invalid content type.", status_code=400)

    model_class = content_type.model_class()
    if not model_class:
        raise LocalBaseException("Could not resolve model from content type.", status_code=400)

    instance = model_class.objects.filter(pk=object_id).first()
    if not instance:
        raise LocalBaseException("Referenced object not found.", status_code=404)

    return instance

def get_content_type_and_object_id(
    obj_or_id: Union[Model, str],
    candidate_models: list[Type[Model]],
    return_ct_instance=False
) -> tuple[int, str]:
    """
    Given a model instance or ID, resolve its content_type ID and object ID.
    Searches across provided candidate models.
    """

    # 🛑 Prevent using RelatedManager by mistake
    if hasattr(obj_or_id, "all") and isinstance(obj_or_id, BaseManager):
        raise LocalBaseException(exception="Invalid object: got a related manager instead of an instance or ID.")

    if isinstance(obj_or_id, Model):
        ct = ContentType.objects.get_for_model(obj_or_id.__class__)
        if return_ct_instance:
            return ct , str(obj_or_id.pk)
        return ct.pk, str(obj_or_id.pk)

    for model in candidate_models:
        instance = model.objects.filter(pk=obj_or_id).first()
        if instance:
            ct = ContentType.objects.get_for_model(model)
            if return_ct_instance:
                return ct , str(instance.pk)
            return ct.pk, str(instance.pk)
    raise LocalBaseException(exception="Invalid ID or related model")

def get_objects_by_gfk(model_class: Model, id: str, related_models: list, *q_params, **params):
    """
        Returns a queryset from self.model_class filtered by content_type + object_id = id,
        searching across multiple related models (e.g., Equipment, Attachment).
        
        Accepts optional positional (Q objects) and keyword filters.
        Returns the first non-empty queryset or None.
    """
    ct, obj_id = get_content_type_and_object_id(id, related_models)
    return model_class.objects.filter(content_type=ct, object_id=obj_id, *q_params, **params)