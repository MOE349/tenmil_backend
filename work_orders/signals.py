# work_orders/signals.py
from django.db import ProgrammingError, OperationalError
from work_orders.models import MaintenanceType, WorkOrderCompletionNote, WorkOrderStatusNames
from core.models import HighLevelMaintenanceType, WorkOrderStatusControls

def create_default_status_names(sender, **kwargs):
    try:
        if WorkOrderStatusNames.objects.count() == 0:
            for control in WorkOrderStatusControls.objects.all():
                WorkOrderStatusNames.objects.get_or_create(
                    name=control.name,
                    control=control,
                    is_system_level=True
                )
    except (ProgrammingError, OperationalError):
        # Tables might not exist yet during first migration or test runs
        pass

def create_default_maint_types(sender, **kwargs):
    try:
        if MaintenanceType.objects.count() == 0:
            for control in HighLevelMaintenanceType.objects.all():
                MaintenanceType.objects.get_or_create(
                    name=control.name,
                    control=control,
                    is_system_level=True
                )
    except (ProgrammingError, OperationalError):
        # Tables might not exist yet during first migration or test runs
        pass

    
def create_work_order_completion_note(sender, created, instance, **kwargs):
    work_order = instance
    WorkOrderCompletionNote.objects.get_or_create(work_order=work_order)
        