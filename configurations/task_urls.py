from django.urls import path
from . import task_views

urlpatterns = [
    # Task trigger endpoints
    path('sample/', task_views.trigger_sample_task, name='trigger_sample_task'),
    path('error-log/', task_views.trigger_error_log, name='trigger_error_log'),
    path('background/', task_views.trigger_background_task, name='trigger_background_task'),
    
    # Task status and management endpoints
    path('status/<str:task_id>/', task_views.get_task_status, name='get_task_status'),
    path('active/', task_views.list_active_tasks, name='list_active_tasks'),
    path('cancel/<str:task_id>/', task_views.cancel_task, name='cancel_task'),
] 