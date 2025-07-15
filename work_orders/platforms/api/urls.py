from django.urls import path
from work_orders.platforms.api.views import *


urlpatterns = [
path('work_order', WorkOrderApiView.as_view(), name='WorkOrder'),
path('work_order/<str:pk>', WorkOrderApiView.as_view(), name='WorkOrder'),

path('status', WorkOrderStatusNamesApiView.as_view(), name='WorkOrder status'),
path('status/<str:pk>', WorkOrderStatusNamesApiView.as_view(), name='WorkOrder status'),

path('controls', WorkOrderControlsApiView.as_view(), name='WorkOrder Control'),
path('controls/<str:pk>', WorkOrderControlsApiView.as_view(), name='WorkOrder Control'),

# WorkOrderChecklist endpoints
path('work_orders/checklists', WorkOrderChecklistApiView.as_view(), name='WorkOrderChecklist'),
path('work_orders/checklists/<str:pk>', WorkOrderChecklistApiView.as_view(), name='WorkOrderChecklist'), 

path('work_order_log', WorkOrderLogApiView.as_view(), name='WorkOrderLog'),
path('work_order_log/<str:pk>', WorkOrderLogApiView.as_view(), name='WorkOrderLog'),
path('work_order_misc_cost', WorkOrderMiscCostApiView.as_view(), name='WorkOrderMiscCost'), 
path('work_order_misc_cost/<str:pk>', WorkOrderMiscCostApiView.as_view(), name='WorkOrderMiscCostDetails'),
path('work_order_completion_note', WWorkOrderCompletionNoteApiView.as_view(), name='WorkOrderCompletionNote'),
path('work_order_completion_note/<str:pk>', WWorkOrderCompletionNoteApiView.as_view(), name='WorkOrderCompletionNoteDetails'),

]