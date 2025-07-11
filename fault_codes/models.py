from configurations.base_features.db.base_model import BaseModel
from django.db import models
from tenant_users.models import TenantUser as User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class FaultCode(BaseModel):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    asset = GenericForeignKey("content_type", "object_id")
    code = models.CharField(max_length=255)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)


