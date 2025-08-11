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
        print(f"Creating default maintenance types: {HighLevelMaintenanceType.objects.count()}, {MaintenanceType.objects.count()}")
        if MaintenanceType.objects.count() < HighLevelMaintenanceType.objects.count():
            for hlmtype in HighLevelMaintenanceType.objects.all():
                try:
                    MaintenanceType.objects.get_or_create(
                        name=hlmtype.name,
                        hlmtype=hlmtype,
                        is_system_level=True
                    )
                    print(f"Created maintenance type: {hlmtype.name}")
                except:
                    continue
    except (ProgrammingError, OperationalError):
        # Tables might not exist yet during first migration or test runs
        pass

    
def create_work_order_completion_note(sender, created, instance, **kwargs):
    work_order = instance
    WorkOrderCompletionNote.objects.get_or_create(work_order=work_order)
        