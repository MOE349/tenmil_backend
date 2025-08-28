from django.urls import path, include
from rest_framework.routers import DefaultRouter
from parts.platforms.api.views import (
    PartApiView, InventoryBatchApiView, WorkOrderPartApiView, WorkOrderPartRequestApiView,
    PartMovementApiView, WorkOrderPartMovementApiView, InventoryOperationsApiView,
    WorkOrderPartRequestWorkflowApiView, WorkOrderPartRequestLogApiView
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
    
    path('work-order-part-requests', WorkOrderPartRequestApiView.as_view(), name='work-order-part-requests-list'),
    path('work-order-part-requests/<uuid:pk>', WorkOrderPartRequestApiView.as_view(), name='work-order-part-requests-detail'),
    
    path('movements', PartMovementApiView.as_view(), name='movements-list'),
    path('movements/<uuid:pk>', PartMovementApiView.as_view(), name='movements-detail'),
    
    path('work-order-parts-log', WorkOrderPartMovementApiView.as_view(), name='work-order-parts-log-list'),
    path('work-order-parts-log/<uuid:pk>', WorkOrderPartMovementApiView.as_view(), name='work-order-parts-log-detail'),
    
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
    
    # Workflow endpoints for WorkOrderPartRequest
    path('work-order-part-requests/pending', 
         WorkOrderPartRequestWorkflowApiView.as_view({'get': 'pending_requests'}), 
         name='wopr-pending-requests'),
    
    path('work-order-part-requests/<uuid:pk>/request', 
         WorkOrderPartRequestWorkflowApiView.as_view({'post': 'request_parts'}), 
         name='wopr-request'),
    
    path('work-order-part-requests/<uuid:pk>/confirm-availability', 
         WorkOrderPartRequestWorkflowApiView.as_view({'post': 'confirm_availability'}), 
         name='wopr-confirm-availability'),
    
    path('work-order-part-requests/<uuid:pk>/mark-ordered', 
         WorkOrderPartRequestWorkflowApiView.as_view({'post': 'mark_ordered'}), 
         name='wopr-mark-ordered'),
    
    path('work-order-part-requests/<uuid:pk>/deliver', 
         WorkOrderPartRequestWorkflowApiView.as_view({'post': 'deliver_parts'}), 
         name='wopr-deliver'),
    
    path('work-order-part-requests/<uuid:pk>/pickup', 
         WorkOrderPartRequestWorkflowApiView.as_view({'post': 'pickup_parts'}), 
         name='wopr-pickup'),
    
    path('work-order-part-requests/<uuid:pk>/cancel-availability', 
         WorkOrderPartRequestWorkflowApiView.as_view({'post': 'cancel_availability'}), 
         name='wopr-cancel-availability'),
    
    # Audit log endpoints
    path('work-order-part-requests/<uuid:pk>/audit-log', 
         WorkOrderPartRequestLogApiView.as_view(), 
         name='wopr-audit-log'),
    
    path('work-order-part-request-logs', 
         WorkOrderPartRequestLogApiView.as_view(), 
         name='wopr-logs-list'),
    
    path('work-order-part-request-logs/<uuid:pk>', 
         WorkOrderPartRequestLogApiView.as_view(), 
         name='wopr-logs-detail'),
]