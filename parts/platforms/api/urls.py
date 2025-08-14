"""
API URLs for Parts & Inventory Module
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PartApiView, InventoryBatchApiView, WorkOrderPartApiView, PartMovementApiView
)
from .inventory_views import InventoryOperationsApiView, WorkOrderPartsApiView

# Create router for standard CRUD operations
router = DefaultRouter()

# Register viewsets (if using ViewSet pattern)
# For now, we'll use manual URL patterns since we're extending BaseAPIView

app_name = 'parts_api'

urlpatterns = [
    # Standard CRUD endpoints for model management
    path('parts/', PartApiView.as_view(), name='parts'),
    path('parts/<uuid:pk>/', PartApiView.as_view(), name='part-detail'),
    
    path('inventory-batches/', InventoryBatchApiView.as_view(), name='inventory-batches'),
    path('inventory-batches/<uuid:pk>/', InventoryBatchApiView.as_view(), name='inventory-batch-detail'),
    
    path('work-order-parts/', WorkOrderPartApiView.as_view(), name='work-order-parts'),
    path('work-order-parts/<uuid:pk>/', WorkOrderPartApiView.as_view(), name='work-order-part-detail'),
    
    path('movements/', PartMovementApiView.as_view(), name='movements'),
    path('movements/<uuid:pk>/', PartMovementApiView.as_view(), name='movement-detail'),
    
    # Inventory operations endpoints
    path('inventory/receive/', InventoryOperationsApiView.as_view({'post': 'receive_parts'}), name='inventory-receive'),
    path('inventory/issue/', InventoryOperationsApiView.as_view({'post': 'issue_parts'}), name='inventory-issue'),
    path('inventory/return/', InventoryOperationsApiView.as_view({'post': 'return_parts'}), name='inventory-return'),
    path('inventory/transfer/', InventoryOperationsApiView.as_view({'post': 'transfer_parts'}), name='inventory-transfer'),
    
    # Inventory query endpoints
    path('inventory/on-hand/', InventoryOperationsApiView.as_view({'get': 'get_on_hand'}), name='inventory-on-hand'),
    path('inventory/batches/', InventoryOperationsApiView.as_view({'get': 'get_batches'}), name='inventory-batches'),
    path('inventory/movements/', InventoryOperationsApiView.as_view({'get': 'get_movements'}), name='inventory-movements'),
    
    # Work order specific endpoints
    path('work-orders/<uuid:pk>/parts/', WorkOrderPartsApiView.as_view({'get': 'get_work_order_parts'}), name='work-order-parts'),
]

# Add router URLs if using ViewSets
urlpatterns += router.urls