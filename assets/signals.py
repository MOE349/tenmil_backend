
# from django.dispatch import receiver
from financial_reports.models import CapitalCost




def create_asset(sender, instance, created, **kwargs):
    if created:
        CapitalCost.objects.create(asset=instance.asset_ptr)