from django.contrib import admin
from parts.models import Part, InventoryBatch, WorkOrderPart, PartMovement, IdempotencyKey


admin.site.register(Part)
admin.site.register(InventoryBatch)
admin.site.register(WorkOrderPart)
admin.site.register(PartMovement)
admin.site.register(IdempotencyKey)
