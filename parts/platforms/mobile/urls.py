from django.urls import path
from parts.platforms.mobile.views import (
    PartMobileView, InventoryBatchMobileView, WorkOrderPartMobileView, 
    PartMovementMobileView
)


urlpatterns = [
    path('part', PartMobileView.as_view(), name='Part'), 
    path('inventory_batch', InventoryBatchMobileView.as_view(), name='InventoryBatch'), 
    path('work_order_part', WorkOrderPartMobileView.as_view(), name='WorkOrderPart'), 
    path('part_movement', PartMovementMobileView.as_view(), name='PartMovement'), 
]