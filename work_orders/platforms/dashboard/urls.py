from django.urls import path
from work_orders.platforms.dashboard.views import *


urlpatterns = [
path('work_order', WorkOrderDashboardView.as_view(), name='WorkOrder'), 
path('work_order/<str:pk>', WorkOrderDashboardView.as_view(), name='WorkOrder'),

path('status', WorkOrderStatusNamesDashboardView.as_view(), name='WorkOrder status'),
path('status/<str:pk>', WorkOrderStatusNamesDashboardView.as_view(), name='WorkOrder status'),

path('controls', WorkOrderStatusControlsDashboardView.as_view(), name='WorkOrder Control'),
path('controls/<str:pk>', WorkOrderStatusControlsDashboardView.as_view(), name='WorkOrder Control'),

# WorkOrderChecklist endpoints
path('work_orders/checklists', WorkOrderChecklistDashboardView.as_view(), name='WorkOrderChecklist'),
path('work_orders/checklists/<str:pk>', WorkOrderChecklistDashboardView.as_view(), name='WorkOrderChecklist'), 

path('work_order_log', WorkOrderLogDashboardView.as_view(), name='WorkOrderLog'),
path('work_order_log/<str:pk>', WorkOrderLogDashboardView.as_view(), name='WorkOrderLog'),
path('work_order_misc_cost', WorkOrderMiscCostDashboardView.as_view(), name='WorkOrderMiscCost'), 
path('work_order_misc_cost/<str:pk>', WorkOrderMiscCostDashboardView.as_view(), name='WorkOrderMiscCostDetails'),
path('work_order_completion_note', WorkOrderCompletionNoteDashboardView.as_view(), name='WorkOrderCompletionNote'),
path('work_order_completion_note/<str:pk>', WorkOrderCompletionNoteDashboardView.as_view(), name='WorkOrderCompletionNoteDetails'),

# Import asset backlogs endpoint
path('work_order/<str:pk>/import-backlogs', WorkOrderImportBacklogsDashboardView.as_view(), name='WorkOrderImportBacklogs'),

# Work order completion endpoint
path('work_order/<str:pk>/complete', WorkOrderCompletionDashboardView.as_view(), name='WorkOrderCompletion'),

]