from work_orders.models import *
from django.contrib import admin


admin.site.register(WorkOrder)
admin.site.register(WorkOrderChecklist)
admin.site.register(WorkOrderLog)
admin.site.register(WorkOrderMiscCost)
