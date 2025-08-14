from parts.models import *
from django.contrib import admin


admin.site.register(Part)
admin.site.register(InventoryBatch)
admin.site.register(WorkOrderPart)
admin.site.register(PartMovement)
admin.site.register(IdempotencyKey)
