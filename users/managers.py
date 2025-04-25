from django.contrib.auth.models import BaseUserManager

from configurations.base_features.db.base_manager import BaseManager


class UserManager(BaseUserManager, BaseManager):
    def create_user(self, email, name, password=None, **extra_fields):
        print("UserManager create_user ", email)
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        email = email.lower()
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()
        return user
    
    def create_superuser(self, email, name, password=None, **extra_fields):
        user = self.create_user(email, name, password, **extra_fields)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()
        return user