"""
API URLs for Parts & Inventory Module
"""

from django.urls import path

from .views import (
    PartApiView, InventoryBatchApiView, WorkOrderPartApiView, PartMovementApiView
)
from .inventory_views import (
    InventoryReceiveApiView, InventoryIssueApiView, InventoryReturnApiView, 
    InventoryTransferApiView, InventoryOnHandApiView, InventoryBatchesApiView, 
    InventoryMovementsApiView, WorkOrderPartsApiView, PartLocationsSummaryApiView
)

app_name = 'parts_api'

urlpatterns = [
    # Standard CRUD endpoints for model management
    path('parts', PartApiView.as_view(), name='parts'),
    path('parts/<uuid:pk>', PartApiView.as_view(), name='part-detail'),
    
    path('inventory-batches', InventoryBatchApiView.as_view(), name='inventory-batches'),
    path('inventory-batches/<uuid:pk>', InventoryBatchApiView.as_view(), name='inventory-batch-detail'),
    
    path('work-order-parts', WorkOrderPartApiView.as_view(), name='work-order-parts'),
    path('work-order-parts/<uuid:pk>', WorkOrderPartApiView.as_view(), name='work-order-part-detail'),
    
    path('movements', PartMovementApiView.as_view(), name='movements'),
    path('movements/<uuid:pk>', PartMovementApiView.as_view(), name='movement-detail'),
    
    # Inventory operations endpoints
    path('inventory/receive/', InventoryReceiveApiView.as_view(), name='inventory-receive'),
    path('inventory/issue/', InventoryIssueApiView.as_view(), name='inventory-issue'),
    path('inventory/return/', InventoryReturnApiView.as_view(), name='inventory-return'),
    path('inventory/transfer/', InventoryTransferApiView.as_view(), name='inventory-transfer'),
    
    # Inventory query endpoints
    path('inventory/on-hand/', InventoryOnHandApiView.as_view(), name='inventory-on-hand'),
    path('inventory/batches/', InventoryBatchesApiView.as_view(), name='inventory-batches'),
    path('inventory/movements/', InventoryMovementsApiView.as_view(), name='inventory-movements'),
    path('inventory/locations-summary/', PartLocationsSummaryApiView.as_view(), name='inventory-locations-summary'),
    
    # Work order specific endpoints
    path('work-orders/<uuid:pk>/parts/', WorkOrderPartsApiView.as_view(), name='work-order-parts'),
]