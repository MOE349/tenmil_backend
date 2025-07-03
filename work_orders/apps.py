# work_orders/apps.py
from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.db import connection

class WorkOrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'work_orders'

    def ready(self):
        from .signals import create_default_status_names  # noqa
        post_migrate.connect(create_default_status_names, sender=self)
