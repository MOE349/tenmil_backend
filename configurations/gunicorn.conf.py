# gunicorn.conf.py

import multiprocessing
import os

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2 * workers
worker_class = "sync"
timeout = 120
preload_app = True  # enables when_ready()

accesslog = "-"
errorlog = "-"

def when_ready(server):
    import django
    from django.conf import settings
    from django.db import connection

    print("[Gunicorn] Initializing Django...")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'configurations.settings')
    django.setup()

    print("[Gunicorn] Running system_start_checks()")
    from configurations.system_start_checks import system_start_checks, Tenant
    system_start_checks()
    print(f"tenant names: {Tenant.objects.all().values_list('schema_name', flat=True)}")
    print({
        "ping": "pong",
        "schema": connection.schema_name,
        "tenant": str(getattr(connection, "tenant", None)),
        "urlconf": settings.ROOT_URLCONF,
        "settings_module": os.environ.get("DJANGO_SETTINGS_MODULE", "not set"),
        "debug": settings.DEBUG,
    })