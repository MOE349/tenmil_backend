from django.db.models.signals import post_save
from django.dispatch import receiver
from company.models import Site, Location
from configurations.base_features.helpers.text_helpers import slugify


@receiver(post_save, sender=Site)
def create_location(sender, instance, created, **kwargs):
    if created:
        Location.objects.create(
            site=instance, name=instance.name, slug=slugify(instance.name))
