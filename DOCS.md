# Tenmil Backend Foundation Documentation

This documentation describes the foundational components and conventions used across all backend apps in the **Tenmil** platform. It covers reusable base classes, app architecture, custom code generation, and environment configurations.

---

## 📁 Core Architecture

### ✅ Modular App Structure

Each Django app in Tenmil follows a standardized structure:

```
<app_name>/
├── admin.py
├── apps.py
├── models.py
├── tests.py
├── platforms/
│   ├── base/
│   │   ├── serializers.py
│   │   └── views.py
│   ├── api/
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── urls.py
│   ├── dashboard/
│   └── mobile/
└── migrations/
```

* `base`: Holds default logic for views/serializers.
* `api`, `dashboard`, `mobile`: Platform-specific overrides.
* `platforms/.../urls.py`: Route per platform.

Apps are generated using the custom `create_app` management command.

---

## ⚙️ Base Classes

### `LocalBaseException`

A translated, structured exception with safe handling:

```python
class LocalBaseException(Exception):
    def __init__(self, exception_type=None, status_code=500, lang='en', exception=None, kwargs=None):
        ...
    def to_dict(self): ...
    def log(self): ...
    def get_response(self): ...
```

Supports translation, structured error data, and auto-logging.

---

### `BaseModel`

UUID-based abstract base model:

```python
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

---

### `SafeDeleteModel`

Adds soft-delete functionality:

```python
class SafeDeleteModel(BaseModel):
    is_deleted = models.BooleanField(default=False)

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()
```

---

### `BaseManager`

Custom queryset manager:

```python
class BaseManager(models.Manager):
    def not_deleted(self): ...
    def active(self): ...
    def get_or_none(self, **kwargs): ...
    def create_or_update(self, filters, defaults): ...
```

---

### `BaseSerializer`

Centralized DRF serializer abstraction:

```python
class BaseSerializer(ModelSerializer):
    def mod_create(self, validated_data): ...
    def mod_update(self, instance, validated_data): ...
    def mod_to_representation(self, instance): ...
```

Override the `mod_` methods instead of DRF core methods.

---

### `BaseApiView`

Abstract API view with full CRUD:

```python
class BaseApiView(AuthMixin, ResponseFormatterMixin, BaseExceptionHandlerMixin, APIView):
    allowed_roles = None
    model_class = None
    serializer_class = None
    ...
```

Handles authentication, exception formatting, role validation, and CRUD logic.

---

### Mixins Used in BaseApiView

* `AuthMixin`: JWT + role-based tenant auth.
* `BaseExceptionHandlerMixin`: Smart traceback + error serialization.
* `ResponseFormatterMixin`: Unifies success/error response shape.

---

## ⚙️ App Generator System

Located in `custom_commands/`, this system allows automated generation of apps:

### `create_app.py`

Main entry point via CLI:

```bash
python manage.py create_app --app_name=assets --platforms=api dashboard mobile --models=equipment request
```

### Components

* `AppGenerator`: Orchestrates app creation.
* `ModelGenerator`: Creates models.py.
* `PlatformGenerator`: Builds base and per-platform serializers, views, and urls.
* `BaseGenerator`: Utilities for file and folder operations.

All platform-specific serializers and views inherit from `base`.

---

## ⚙️ Settings Overview

### Modular Settings

Settings are split across:

* `base.py`: Core Django setup
* `database.py`: Uses `env()` and switches between STAGE/PROD
* `cors_headers_config.py`: CORS/Credentials
* `rest_framework.py`: JWT (10d access, 100d refresh)
* `tenants.py`: Public schema routing and tenant model setup

### Multitenancy

* Uses `django-tenants`
* Tenant detection via subdomain (`SubdomainTenantMiddleware`)
* Admin runs on `admin.tenmil.com`, public schema only

---

## ✅ Best Practices

### For Apps

* Base logic lives in `platforms/base`
* Override methods in `api`, `mobile`, `dashboard` as needed
* Always inherit from base serializer/view

### For Exceptions

* Raise `LocalBaseException()` with type or message
* Use `.to_dict()` for logging or `.get_response()` for API

### For Serializers

* Extend `BaseSerializer`
* Override `mod_create`, `mod_update`, `mod_to_representation`

---

## 🧠 Memory

All core classes and conventions above are remembered across sessions.
Use them freely while building or debugging apps.

---

> Next Step: Start app-level development using `create_app`, and override base logic only where needed.
