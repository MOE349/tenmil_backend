from django.db import models
from .base_model import BaseModel

class SafeDeleteModel(BaseModel):
    """
    Adds soft-delete functionality by overriding delete() method.
    """
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save(update_fields=["is_deleted", "updated_at"])
