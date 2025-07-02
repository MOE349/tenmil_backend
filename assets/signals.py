
# from django.dispatch import receiver
from assets.services import get_content_type_and_asset_id
from financial_reports.models import CapitalCost



def create_asset(sender, instance, created, **kwargs):
    if created:
        ct, obj_id = get_content_type_and_asset_id(instance.id, return_ct_instance=True)
        CapitalCost.objects.create(object_id=obj_id, content_type=ct)