from configurations.base_features.db.base_manager import BaseManager
from django.db import models


class AssetQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_online=True)

    def by_site(self, site_id):
        return self.filter(location__site_id=site_id)


class AssetManager(BaseManager.from_queryset(AssetQuerySet)):
    pass
