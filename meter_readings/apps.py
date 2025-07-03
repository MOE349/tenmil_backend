from django.apps import AppConfig


class MeterReadingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'meter_readings'

    def ready(self) -> None:
        ready = super().ready()
        # from meter_readings.signals import create_meter_reading, updated_work_order  # noqa
        # from meter_readings.models import MeterReading  # noqa
        # from django.db.models.signals import post_save  # noqa
        # from work_orders.models import WorkOrder  # noqa

        # post_save.connect(create_meter_reading, sender=MeterReading)
        # post_save.connect(updated_work_order, sender=WorkOrder)

        return ready