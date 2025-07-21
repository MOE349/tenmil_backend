from django.contrib.contenttypes.models import ContentType
from assets.models import *
from typing import Union
from django.db.models import Model

from assets.platforms.base.serializers import AssetBaseSerializer, AttachmentBaseSerializer, EquipmentBaseSerializer
from configurations.base_features.db.db_helpers import get_content_type_and_object_id, get_objects_by_gfk


def get_asset_serializer(instance, *args, **kwargs):
    if isinstance(instance, Equipment):
        return EquipmentBaseSerializer(instance, *args, **kwargs)
    elif isinstance(instance, Attachment):
        return AttachmentBaseSerializer(instance, *args, **kwargs)
    return AssetBaseSerializer(instance, *args, **kwargs)  # fallback if needed



def get_assets_by_gfk(model_class, id, *q_params, **params):
    return get_objects_by_gfk(model_class, id, [Equipment, Attachment],  *q_params, **params)


def get_content_type_and_asset_id(
    obj_or_id: Union[Model, str],
    return_ct_instance=False,
    return_instance=False
) -> tuple[int, str]:
    return get_content_type_and_object_id(obj_or_id, [Equipment, Attachment], return_ct_instance=return_ct_instance, return_instance=return_instance)


def move_asset(asset, from_location, to_location, user=None):
    if from_location == to_location:
        return

    log = AssetMovementLog.objects.create(
        content_type=ContentType.objects.get_for_model(asset),
        object_id=asset.id,
        asset=asset,
        from_location=from_location,
        to_location=to_location,
        moved_by=user,
    )
    print(f"move_asset from {log.from_location} to {log.to_location}")
    return log

