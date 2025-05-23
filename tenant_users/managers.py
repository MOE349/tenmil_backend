from django.contrib.auth.base_user import BaseUserManager

class TenantUserManager(BaseUserManager):
    def create_user(self, email, name, tenant, password=None, **extra_fields):
        if not email or not tenant:
            raise ValueError("Users must have an email address and tenant")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, tenant=tenant, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user