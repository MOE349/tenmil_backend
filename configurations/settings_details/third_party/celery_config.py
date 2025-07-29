import os
from configurations.settings_details.env import env

# Celery Configuration Options

# Redis configuration - supports both local and production
REDIS_HOST = env('REDIS_HOST', default='localhost')
REDIS_PORT = env('REDIS_PORT', default='6379')
REDIS_PASSWORD = env('REDIS_PASSWORD', default='')
REDIS_DB = env('REDIS_DB', default='0')

# Build Redis URL
if REDIS_PASSWORD:
    CELERY_BROKER_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
    CELERY_RESULT_BACKEND = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
else:
    CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
    CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Fallback to environment variable if set
CELERY_BROKER_URL = env('REDIS_URL', default=CELERY_BROKER_URL)
CELERY_RESULT_BACKEND = env('REDIS_URL', default=CELERY_RESULT_BACKEND)

# Celery Settings
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'

# Celery Beat Configuration
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Task configuration
CELERY_TASK_ALWAYS_EAGER = False  # Set to True for testing
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_TASK_IGNORE_RESULT = False
CELERY_TASK_STORE_EAGER_RESULT = True

# Worker configuration
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Task retry configuration
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Security
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_TASK_ALWAYS_EAGER', default=False)

# Result expiration
CELERY_RESULT_EXPIRES = 3600  # 1 hour

# Connection pool settings for production
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10

# Task routing (optional - for advanced usage)
CELERY_TASK_ROUTES = {
    'pm_automation.tasks.*': {'queue': 'automation'},
    'assets.tasks.*': {'queue': 'assets'},
    'financial_reports.tasks.*': {'queue': 'reports'},
    # Add more app-specific queues as needed
}

# Default queue
CELERY_TASK_DEFAULT_QUEUE = 'default'
