from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from configurations.base_features.db.base_model import BaseModel
from core.models import Tenant
from tenant_users.managers import TenantUserManager

class TenantUser(BaseModel, AbstractBaseUser, PermissionsMixin):
    email = models.EmailField()
    name = models.CharField(max_length=255)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'tenant']

    objects = TenantUserManager()

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='tenant_users',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='tenant_users_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    class Meta:
        unique_together = ('email', 'tenant')  # same email allowed in different tenants

    def __str__(self):
        return f"{self.email} @ {self.tenant}"