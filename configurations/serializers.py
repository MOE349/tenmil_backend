# from rest_framework.serializers import Serializer

# from assets.models import Asset
# from work_orders.models import *

# class DashboardApiSerializer(Serializer):
#     def to_representation(self, *args, **kwargs):
#         assets =  Asset.objects.all().order_by("-created_at")
#         work_orders = WorkOrder.objects.all().order_by("-created_at")
#         work_order_logs = WorkOrderLog.objects.all().order_by("-created_at")[:10]
#         work_order_checklist = WorkOrderChecklist.objects.filter(assigned_to=None)
#         number = 1
#         for wo in work_orders:
#             if not wo.code:
#                 wo.code = f"WO_{number}"
#                 wo.save()
#                 number += 1
#         top_assets = assets[:5]
#         utilization = [ 60,15, 80, 25, 90]
#         top_assets_utilization =  []
#         for asset, util in zip(top_assets, utilization):
#             top_assets_utilization.append([str(asset.id), asset.code, "Online" if asset.is_online else "Offline", util])
#         response = {}
#         response['open_work_orders_count'] = work_orders.filter(status__control__name='Active').count()
#         response['online_assets_count'] = assets.filter(is_online=True).count()
#         response['top_assets_utilization'] = top_assets_utilization
#         response['work_orders_by_status'] = [{"id":wo.id, "code": wo.code, "status":f"{wo.status.name}-{wo.status.control.name}"} for wo in work_orders.order_by("status__control__name")[:8]]
#         response['scheduled_maintenance_count'] = 0
        
#         response['unassigned_taskes_count'] = work_order_checklist.count()
#         response['upcomming_maintenance'] = ["Under constraction"]
#         response['recent_user_activity'] = [f"{wol.user.name.title()} {wol.log_type.lower()} {wol.work_order.code}" for wol in work_order_logs]

#         return response