from django.urls import path
from parts.platforms.dashboard.views import *


urlpatterns = [
path('Part', PartDashboardView.as_view(), name='Part'), 
path('InventoryBatch', InventorybatchDashboardView.as_view(), name='Inventorybatch'), 
path('WorkOrderPart', WorkorderpartDashboardView.as_view(), name='Workorderpart'), 
path('PartMovement', PartmovementDashboardView.as_view(), name='Partmovement'), 

]