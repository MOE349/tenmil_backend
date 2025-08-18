from django.urls import path
from parts.platforms.mobile.views import *


urlpatterns = [
path('Part', PartMobileView.as_view(), name='Part'), 
path('InventoryBatch', InventorybatchMobileView.as_view(), name='Inventorybatch'), 
path('WorkOrderPart', WorkorderpartMobileView.as_view(), name='Workorderpart'), 
path('PartMovement', PartmovementMobileView.as_view(), name='Partmovement'), 

]