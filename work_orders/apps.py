# work_orders/apps.py
from django.apps import AppConfig
from django.db.models.base import post_save
from django.db.models.signals import post_migrate
from django.db import connection


class WorkOrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'work_orders'

    def ready(self):
        from .signals import create_default_status_names, create_work_order_completion_note  # noqa
        post_migrate.connect(create_default_status_names, sender=self)
        post_save.connect(create_work_order_completion_note, sender=self, dispatch_uid='create_work_order_completion_note')
