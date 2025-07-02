import uuid
from django.db import models
from .base_manager import BaseManager

class BaseModel(models.Model):
    """
    Abstract base model with UUID primary key, timestamps, and custom manager.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BaseManager()

    class Meta:
        abstract = True

    def __str__(self):
        for field in ["name", "title", "code"]:
            if hasattr(self, field):
                return str(getattr(self, field))
        return str(self.id)
