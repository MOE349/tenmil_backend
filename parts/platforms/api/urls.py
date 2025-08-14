from django.urls import path
from parts.platforms.api.views import *


urlpatterns = [
path('part', PartApiView.as_view(), name='Part'), 
path('inventory_batch', InventoryBatchApiView.as_view(), name='InventoryBatch'), 
path('work_order_part', WorkOrderPartApiView.as_view(), name='WorkOrderPart'), 
path('part_movement_log', PartMovementLogApiView.as_view(), name='PartMovementLog'), 

]