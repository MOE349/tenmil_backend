from django.urls import path
from parts.platforms.dashboard.views import *


urlpatterns = [
path('part', PartDashboardView.as_view(), name='Part'), 
path('inventory_batch', InventoryBatchDashboardView.as_view(), name='InventoryBatch'), 
path('work_order_part', WorkOrderPartDashboardView.as_view(), name='WorkOrderPart'), 
path('part_movement_log', PartMovementLogDashboardView.as_view(), name='PartMovementLog'), 

]