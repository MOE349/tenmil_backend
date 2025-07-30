import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configurations.settings')

app = Celery('tenmil_backend')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Optional: Configure Celery to work with multi-tenant setup
from django_tenants.utils import tenant_context
from django_tenants.utils import get_tenant_model

def get_tenant_specific_task():
    """Decorator to run tasks in tenant context"""
    def decorator(task_func):
        def wrapper(*args, **kwargs):
            tenant_schema = kwargs.pop('tenant_schema', None)
            if tenant_schema:
                Tenant = get_tenant_model()
                try:
                    tenant = Tenant.objects.get(schema_name=tenant_schema)
                    with tenant_context(tenant):
                        return task_func(*args, **kwargs)
                except Tenant.DoesNotExist:
                    raise Exception(f"Tenant {tenant_schema} does not exist")
            else:
                return task_func(*args, **kwargs)
        return wrapper
    return decorator

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
    return 'Debug task completed'

# Celery beat configuration
from celery.schedules import crontab

app.conf.beat_schedule = {
    'log-error-every-30-seconds': {
        'task': 'configurations.tasks.log_error_task',
        'schedule': 30.0,  # Every 30 seconds
    },
    'check-calendar-pms': {
        'task': 'configurations.tasks.check_calendar_pms',
        'schedule': crontab(minute=0),  # Every hour
    },
}

app.conf.timezone = 'UTC' 