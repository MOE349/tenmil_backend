from django.apps import AppConfig


class AssetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'assets'

    def ready(self) -> None:
        ready = super().ready()
        from assets.signals import create_asset  # noqa
        from .models import Equipment, Attachment  # noqa
        from django.db.models.signals import post_save

        post_save.connect(receiver=create_asset, sender=Equipment, weak=False, dispatch_uid="Assets_create_equipment")
        post_save.connect(receiver=create_asset, sender=Attachment, weak=False, dispatch_uid="Assets_create_attachment")
        return ready