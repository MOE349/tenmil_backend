# gunicorn.conf.py

import multiprocessing

from configurations.system_start_checks import system_start_checks

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
timeout = 120
preload_app = True  # IMPORTANT: enables `when_ready` hook to work

accesslog = "-"
errorlog = "-"

def when_ready(server):
    print("[Gunicorn] Running system_start_checks()...")
    system_start_checks()
