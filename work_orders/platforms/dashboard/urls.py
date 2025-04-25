from django.urls import path
from work_orders.platforms.dashboard.views import *


urlpatterns = [
path('work_order', WorkOrderDashboardView.as_view(), name='WorkOrder'), 
path('work_order_checklist', WorkOrderChecklistDashboardView.as_view(), name='WorkOrderChecklist'), 
path('work_order_log', WorkOrderLogDashboardView.as_view(), name='WorkOrderLog'), 
path('work_order_misc_cost', WorkOrderMiscCostDashboardView.as_view(), name='WorkOrderMiscCost'), 

]