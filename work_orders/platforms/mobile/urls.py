from django.urls import path
from work_orders.platforms.mobile.views import *


urlpatterns = [
path('work_order', WorkOrderMobileView.as_view(), name='WorkOrder'), 
path('work_order/<str:pk>', WorkOrderMobileView.as_view(), name='WorkOrder'),

path('status', WorkOrderStatusNamesMobileView.as_view(), name='WorkOrder status'),
path('status/<str:pk>', WorkOrderStatusNamesMobileView.as_view(), name='WorkOrder status'),

path('controls', WorkOrderStatusControlsMobileView.as_view(), name='WorkOrder Control'),
path('controls/<str:pk>', WorkOrderStatusControlsMobileView.as_view(), name='WorkOrder Control'),

# WorkOrderChecklist endpoints
path('work_orders/checklists', WorkOrderChecklistMobileView.as_view(), name='WorkOrderChecklist'),
path('work_orders/checklists/<str:pk>', WorkOrderChecklistMobileView.as_view(), name='WorkOrderChecklist'), 

path('work_order_log', WorkOrderLogMobileView.as_view(), name='WorkOrderLog'),
path('work_order_log/<str:pk>', WorkOrderLogMobileView.as_view(), name='WorkOrderLog'),
path('work_order_misc_cost', WorkOrderMiscCostMobileView.as_view(), name='WorkOrderMiscCost'), 
path('work_order_misc_cost/<str:pk>', WorkOrderMiscCostMobileView.as_view(), name='WorkOrderMiscCostDetails'),
path('work_order_completion_note', WorkOrderCompletionNoteMobileView.as_view(), name='WorkOrderCompletionNote'),
path('work_order_completion_note/<str:pk>', WorkOrderCompletionNoteMobileView.as_view(), name='WorkOrderCompletionNoteDetails'),

# Import asset backlogs endpoint
path('work_order/<str:pk>/import-backlogs', WorkOrderImportBacklogsMobileView.as_view(), name='WorkOrderImportBacklogs'),

# Work order completion endpoint
path('work_order/<str:pk>/complete', WorkOrderCompletionMobileView.as_view(), name='WorkOrderCompletion'),

]