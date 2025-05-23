from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from configurations.base_features.db.base_model import BaseModel
from admin_users.managers import AdminUserManager

class AdminUser(BaseModel, AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    objects = AdminUserManager()

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='admin_users',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='admin_users_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def __str__(self):
        return self.email