from django.urls import path, include
from rest_framework.routers import DefaultRouter
from parts.platforms.api.views import (
    PartApiView, InventoryBatchApiView, WorkOrderPartApiView, 
    WorkOrderPartReturnApiView, PartMovementApiView, InventoryOperationsApiView
)

# Create a router for the operations viewset
router = DefaultRouter()
router.register(r'operations', InventoryOperationsApiView, basename='inventory-operations')

urlpatterns = [
    # Standard CRUD endpoints
    path('parts', PartApiView.as_view(), name='parts-list'),
    path('parts/<uuid:pk>', PartApiView.as_view(), name='parts-detail'),
    
    path('inventory-batches', InventoryBatchApiView.as_view(), name='inventory-batches-list'),
    path('inventory-batches/<uuid:pk>', InventoryBatchApiView.as_view(), name='inventory-batches-detail'),
    
    path('work-order-parts', WorkOrderPartApiView.as_view(), name='work-order-parts-list'),
    path('work-order-parts/<uuid:pk>', WorkOrderPartApiView.as_view(), name='work-order-parts-detail'),
    path('work-order-parts/return', WorkOrderPartReturnApiView.as_view(), name='work-order-parts-return'),
    
    path('movements', PartMovementApiView.as_view(), name='movements-list'),
    path('movements/<uuid:pk>', PartMovementApiView.as_view(), name='movements-detail'),
    
    # Operations endpoints via router
    path('', include(router.urls)),
    
    # Additional direct operation endpoints for backward compatibility
    path('receive', InventoryOperationsApiView.as_view({'post': 'receive'}), name='inventory-receive'),
    path('issue', InventoryOperationsApiView.as_view({'post': 'issue'}), name='inventory-issue'),
    path('return', InventoryOperationsApiView.as_view({'post': 'return_parts_action'}), name='inventory-return'),
    path('transfer', InventoryOperationsApiView.as_view({'post': 'transfer'}), name='inventory-transfer'),
    path('on-hand', InventoryOperationsApiView.as_view({'get': 'on_hand'}), name='inventory-on-hand'),
    path('batches', InventoryOperationsApiView.as_view({'get': 'batches'}), name='inventory-batches'),
    path('movements-query', InventoryOperationsApiView.as_view({'get': 'movements'}), name='movements-query'),
    path('locations-on-hand', InventoryOperationsApiView.as_view({'get': 'locations_on_hand'}), name='locations-on-hand'),
    path('locations-on-hand/<uuid:pk>', InventoryOperationsApiView.as_view({'get': 'locations_on_hand'}), name='locations-on-hand'),
    path('get-part-location', InventoryOperationsApiView.as_view({'get': 'get_part_locations'}), name='get-part-location'),
    # Work order specific endpoints
    path('work-orders/<uuid:work_order_id>/parts', 
         InventoryOperationsApiView.as_view({'get': 'get_work_order_parts'}), 
         name='work-order-parts-summary'),
]