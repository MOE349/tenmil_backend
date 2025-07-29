from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse
from celery.result import AsyncResult
from django.views.decorators.csrf import csrf_exempt
import json

# Import tasks
from .tasks import sample_async_task, on_demand_error_log, robust_background_task
from .celery import app as celery_app

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_sample_task(request):
    """
    API endpoint to trigger a sample async task from within the app.
    POST /api/tasks/sample/
    Body: {"message": "Your custom message"}
    """
    try:
        data = request.data
        message = data.get('message', 'Task triggered from API')
        
        # Trigger the task asynchronously
        task_result = sample_async_task.delay(message)
        
        return Response({
            'success': True,
            'task_id': task_result.id,
            'message': 'Sample task has been queued successfully',
            'status': 'PENDING'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_error_log(request):
    """
    API endpoint to trigger an on-demand error log task.
    POST /api/tasks/error-log/
    Body: {"message": "Custom error message"}
    """
    try:
        data = request.data
        custom_message = data.get('message', 'Error triggered via API')
        
        # Trigger the error log task
        task_result = on_demand_error_log.delay(custom_message)
        
        return Response({
            'success': True,
            'task_id': task_result.id,
            'message': 'Error log task has been queued successfully',
            'status': 'PENDING'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_background_task(request):
    """
    API endpoint to trigger a robust background task.
    POST /api/tasks/background/
    Body: {"data": {"key": "value", "any": "data"}}
    """
    try:
        data = request.data.get('data', {})
        
        # Trigger the background task
        task_result = robust_background_task.delay(data)
        
        return Response({
            'success': True,
            'task_id': task_result.id,
            'message': 'Background task has been queued successfully',
            'status': 'PENDING'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_task_status(request, task_id):
    """
    API endpoint to check the status of a task.
    GET /api/tasks/status/{task_id}/
    """
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        
        return Response({
            'task_id': task_id,
            'status': task_result.status,
            'result': task_result.result if task_result.ready() else None,
            'ready': task_result.ready(),
            'successful': task_result.successful() if task_result.ready() else None,
            'failed': task_result.failed() if task_result.ready() else None,
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_active_tasks(request):
    """
    API endpoint to list all active tasks.
    GET /api/tasks/active/
    """
    try:
        # Get active tasks
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        
        # Get scheduled tasks
        scheduled_tasks = inspect.scheduled()
        
        return Response({
            'active_tasks': active_tasks,
            'scheduled_tasks': scheduled_tasks,
            'total_workers': len(active_tasks) if active_tasks else 0
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_task(request, task_id):
    """
    API endpoint to cancel a task.
    POST /api/tasks/cancel/{task_id}/
    """
    try:
        celery_app.control.revoke(task_id, terminate=True)
        
        return Response({
            'success': True,
            'task_id': task_id,
            'message': 'Task has been cancelled'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

# Simple function to trigger tasks programmatically from anywhere in your Django app
def trigger_task_from_code(task_name, *args, **kwargs):
    """
    Helper function to trigger tasks programmatically from within Django code.
    
    Usage:
    from configurations.task_views import trigger_task_from_code
    result = trigger_task_from_code('sample_async_task', message="Hello from code")
    """
    task_mapping = {
        'sample_async_task': sample_async_task,
        'on_demand_error_log': on_demand_error_log,
        'robust_background_task': robust_background_task,
    }
    
    task_func = task_mapping.get(task_name)
    if task_func:
        return task_func.delay(*args, **kwargs)
    else:
        raise ValueError(f"Task '{task_name}' not found. Available tasks: {list(task_mapping.keys())}") 