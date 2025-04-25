from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin

from configurations.base_features.db.base_model import BaseModel
from users.managers import UserManager

class User(BaseModel,AbstractUser, PermissionsMixin):
    username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    objects = UserManager()

