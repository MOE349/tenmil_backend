from django.urls import path
from work_orders.platforms.mobile.views import *


urlpatterns = [
path('work_order', WorkOrderMobileView.as_view(), name='WorkOrder'), 
path('work_order_checklist', WorkOrderChecklistMobileView.as_view(), name='WorkOrderChecklist'), 
path('work_order_log', WorkOrderLogMobileView.as_view(), name='WorkOrderLog'), 
path('work_order_misc_cost', WorkOrderMiscCostMobileView.as_view(), name='WorkOrderMiscCost'), 

]