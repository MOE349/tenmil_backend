import uuid
from django.db import models

from .base_manager import BaseManager


class BaseModel(models.Model):
    id = models.CharField(
        primary_key=True, editable=False, unique=True, default=uuid.uuid4, max_length=50
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BaseManager()

    class Meta:
        abstract = True
