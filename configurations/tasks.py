import logging
from celery import shared_task
from django.utils import timezone
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

@shared_task(bind=True)
def log_error_task(self):
    """
    Periodic task that logs an error message every 30 seconds.
    This task is scheduled in celery.py beat_schedule.
    """
    current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    error_message = f"[SCHEDULED ERROR LOG] This is a test error logged at {current_time} - Task ID: {self.request.id}"
    
    # Log the error using Python's logging system
    logger.error(error_message)
    
    # Also print to console for immediate visibility
    print(f"🔴 ERROR: {error_message}")
    
    return {
        'status': 'completed',
        'message': error_message,
        'timestamp': current_time,
        'task_id': self.request.id
    }

@shared_task
def sample_async_task(message="Hello from Celery!"):
    """
    Sample async task that can be called from within the app.
    Usage: from configurations.tasks import sample_async_task
           result = sample_async_task.delay("Your message here")
    """
    current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"📢 Sample Task executed at {current_time}: {message}")
    
    return {
        'status': 'completed',
        'message': message,
        'timestamp': current_time
    }

@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def robust_background_task(self, data):
    """
    Example of a robust background task with retry logic.
    Useful for operations that might fail and need retry mechanism.
    """
    try:
        # Simulate some work
        print(f"Processing data: {data}")
        current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Your actual task logic goes here
        # For example: sending emails, processing files, API calls, etc.
        
        return {
            'status': 'success',
            'data_processed': data,
            'timestamp': current_time,
            'task_id': self.request.id
        }
        
    except Exception as exc:
        logger.error(f"Task {self.request.id} failed: {str(exc)}")
        # This will trigger the autoretry mechanism
        raise self.retry(exc=exc)

# Task for triggering from within the app (accessible via API or admin)
@shared_task
def on_demand_error_log(custom_message="On-demand error triggered"):
    """
    Task that can be triggered from within the Django app.
    This allows you to schedule tasks programmatically from views, admin, etc.
    """
    current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    error_message = f"[ON-DEMAND ERROR] {custom_message} at {current_time}"
    
    logger.error(error_message)
    print(f"🔴 ON-DEMAND ERROR: {error_message}")
    
    return {
        'status': 'completed',
        'message': error_message,
        'timestamp': current_time
    }

@shared_task(bind=True)
def check_calendar_pms(self):
    """
    Celery task to check for due calendar PMs
    Runs every 15 minutes to check for calendar-based PM work orders that need to be created
    Multi-tenant aware: checks all tenant schemas
    """
    try:
        from pm_automation.calendar_service import CalendarPMService
        from django_tenants.utils import get_tenant_model, schema_context
        from django.db import connection
        
        total_work_orders = []
        tenant_results = {}
        
        # Get all tenant schemas
        tenant_model = get_tenant_model()
        tenants = tenant_model.objects.all()
        
        for tenant in tenants:
            try:
                # Switch to tenant schema
                with schema_context(tenant.schema_name):
                    print(f"📅 Checking calendar PMs for tenant: {tenant.schema_name}")
                    
                    # Check calendar PMs for this tenant
                    created_work_orders = CalendarPMService.check_calendar_pms_due()
                    
                    if created_work_orders:
                        total_work_orders.extend(created_work_orders)
                        tenant_results[tenant.schema_name] = {
                            'work_orders_created': len(created_work_orders),
                            'work_order_ids': [str(wo.id) for wo in created_work_orders]
                        }
                        logger.info(f"📅 Created {len(created_work_orders)} calendar PM work orders for tenant {tenant.schema_name}")
                        print(f"📅 Tenant {tenant.schema_name}: Created {len(created_work_orders)} work orders")
                    else:
                        print(f"📅 Tenant {tenant.schema_name}: No work orders due")
                        
            except Exception as tenant_exc:
                logger.error(f"Error checking calendar PMs for tenant {tenant.schema_name}: {str(tenant_exc)}")
                tenant_results[tenant.schema_name] = {'error': str(tenant_exc)}
        
        result = {
            'status': 'completed',
            'total_work_orders_created': len(total_work_orders),
            'tenants_processed': len(tenants),
            'tenant_results': tenant_results,
            'timestamp': timezone.now().isoformat(),
            'task_id': self.request.id
        }
        
        if total_work_orders:
            logger.info(f"📅 Total: Created {len(total_work_orders)} calendar PM work orders across {len(tenants)} tenants")
            print(f"📅 Calendar PM Check Complete: {len(total_work_orders)} work orders created across {len(tenants)} tenants")
        else:
            print(f"📅 Calendar PM Check Complete: No work orders due across {len(tenants)} tenants at {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return result
        
    except Exception as exc:
        logger.error(f"Error in calendar PM check task: {str(exc)}")
        raise self.retry(exc=exc) 