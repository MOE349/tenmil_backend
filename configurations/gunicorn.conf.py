# gunicorn.conf.py

import multiprocessing
import os

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
timeout = 120
preload_app = True  # enables when_ready()

accesslog = "-"
errorlog = "-"

def when_ready(server):
    import django
    from django.conf import settings

    print("[Gunicorn] Initializing Django...")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")  # adjust this!
    django.setup()

    print("[Gunicorn] Running system_start_checks()")
    from configurations.system_start_checks import system_start_checks, Tenant
    system_start_checks()
    print(f"tenants count = {Tenant.objects.count()}")