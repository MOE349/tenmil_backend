from configurations.base_features.db.base_model import BaseModel
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class AssetBacklog(BaseModel):
    object_id = models.UUIDField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    asset = GenericForeignKey("content_type", "object_id")
    name = models.CharField(max_length=255)


