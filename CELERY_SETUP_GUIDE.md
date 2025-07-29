# Celery and Redis Task Scheduling Setup

This document provides a complete guide for using the Celery and Redis task scheduling system implemented in the Tenmil backend.

## 🚀 Quick Start

### 1. Install Dependencies

The required packages are already added to `requirements.txt`. Install them:

```bash
pip install -r requirements.txt
```

### 2. Setup Redis

Install and start Redis on your system:

**Windows:**
```bash
# Using Chocolatey
choco install redis-64

# Or download from https://github.com/microsoftarchive/redis/releases
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Linux:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

### 3. Database Migration

Run migrations to create the django-celery-beat tables:

```bash
python manage.py migrate
```

### 4. Start the Services

You have several options to start Celery services:

#### Option A: Using Django Management Commands (Recommended)

**Terminal 1: Start Celery Worker**
```bash
python manage.py celery_worker --concurrency=4 --loglevel=INFO
```

**Terminal 2: Start Celery Beat Scheduler**
```bash
python manage.py celery_beat --loglevel=INFO
```

#### Option B: Using Celery Commands Directly
```bash
# Terminal 1: Worker
celery -A configurations worker --loglevel=info

# Terminal 2: Beat
celery -A configurations beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## 📋 Features Implemented

### ✅ Periodic Task: Error Logging Every 30 seconds
- Automatically logs an error message every 30 seconds
- Visible in console output and Django logs
- Task: `configurations.tasks.log_error_task`

### ✅ API Endpoints for Task Management
All endpoints require authentication and are accessible at `/v1/api/tasks/`

- `POST /v1/api/tasks/sample/` - Trigger sample async task
- `POST /v1/api/tasks/error-log/` - Trigger on-demand error log
- `POST /v1/api/tasks/background/` - Trigger background task with retry logic
- `GET /v1/api/tasks/status/{task_id}/` - Check task status
- `GET /v1/api/tasks/active/` - List active tasks
- `POST /v1/api/tasks/cancel/{task_id}/` - Cancel a task

### ✅ Programmatic Task Execution
Execute tasks from within your Django code:

```python
from configurations.task_views import trigger_task_from_code

# Trigger tasks programmatically
result = trigger_task_from_code('sample_async_task', message="Hello from code")
result = trigger_task_from_code('on_demand_error_log', custom_message="Custom error")
```

## 🔧 Configuration

### Environment Variables

**For Local Development** - Add to your `.env` file:
```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
CELERY_TASK_ALWAYS_EAGER=False  # Set to True for testing
```

**For Production (AWS EC2)** - Add to your `.env` file:
```env
# Redis Configuration for AWS EC2
REDIS_HOST=your-ec2-redis-private-ip  # e.g., 172.31.1.100
REDIS_PORT=6379
REDIS_PASSWORD=your_strong_password_here
REDIS_DB=0

# Alternative: Full Redis URL (overrides above settings)
# REDIS_URL=redis://:your_password@your-ec2-ip:6379/0

# Production settings
DEBUG=False
DJANGO_SECRET_KEY=your-production-secret-key-here
CELERY_TASK_ALWAYS_EAGER=False
```

### Celery Settings

Configuration is in `configurations/settings_details/third_party/celery_config.py`:

- **Broker**: Redis
- **Result Backend**: Redis  
- **Serialization**: JSON
- **Timezone**: UTC
- **Database Scheduler**: django-celery-beat

## 📝 Available Tasks

### 1. Periodic Error Log Task
```python
@shared_task(bind=True)
def log_error_task(self):
    # Logs error every 30 seconds (configured in celery.py)
```

### 2. Sample Async Task
```python
@shared_task
def sample_async_task(message="Hello from Celery!"):
    # Basic async task for testing
```

### 3. Robust Background Task
```python
@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3})
def robust_background_task(self, data):
    # Task with automatic retry logic
```

### 4. On-Demand Error Log
```python
@shared_task
def on_demand_error_log(custom_message="On-demand error triggered"):
    # Manually triggered error logging
```

## 🌐 API Usage Examples

### Trigger Sample Task
```bash
curl -X POST http://localhost:8000/v1/api/tasks/sample/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello from API!"}'
```

### Check Task Status
```bash
curl -X GET http://localhost:8000/v1/api/tasks/status/TASK_ID/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### List Active Tasks
```bash
curl -X GET http://localhost:8000/v1/api/tasks/active/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 🔍 Monitoring

### Console Output
- Error logs appear every 30 seconds with 🔴 ERROR prefix
- Task executions show with 📢 prefix
- Task status updates are visible in console

### Django Admin
- Access django-celery-beat admin interface
- Manage periodic tasks: `/admin/django_celery_beat/`
- View task intervals, cron schedules, and task history

### Task Queues
Tasks are organized into queues:
- `default` - General tasks
- `automation` - PM automation tasks
- `assets` - Asset-related tasks  
- `reports` - Financial reports tasks

## 🚨 Troubleshooting

### Redis Connection Issues
```bash
# Check if Redis is running locally
redis-cli ping
# Should return: PONG

# For remote Redis (AWS EC2)
redis-cli -h your-ec2-ip -p 6379 -a your_password ping
# Should return: PONG
```

### Worker Not Processing Tasks
1. Ensure Redis is running
2. Check worker logs for errors
3. Verify CELERY_BROKER_URL in settings
4. Run migrations: `python manage.py migrate`

### Tasks Not Scheduling
1. Ensure Celery Beat is running
2. Check django-celery-beat tables in database
3. Verify beat_schedule in `configurations/celery.py`

### Permission Errors on API
- Ensure you're authenticated with a valid JWT token
- Check user permissions for the endpoints

## 🔧 Development & Testing

### Testing Tasks Locally
Set `CELERY_TASK_ALWAYS_EAGER=True` in your environment to execute tasks synchronously for testing.

### Adding New Tasks
1. Create task functions in appropriate app's `tasks.py`
2. Use `@shared_task` decorator
3. Import in views or call programmatically
4. Add to task routing if needed

### Multi-Tenant Support
The setup includes tenant-aware task execution:

```python
from configurations.celery import get_tenant_specific_task

@get_tenant_specific_task()
@shared_task
def tenant_specific_task(data, tenant_schema=None):
    # Task runs in tenant context
```

## 🚀 AWS EC2 Production Deployment

### Redis Setup on AWS EC2 (Amazon Linux)

1. **Install Redis:**
```bash
# Connect to your EC2 instance
ssh -i your-key.pem ec2-user@your-ec2-ip

# Update system and install Redis
sudo yum update -y
sudo yum install redis -y

# Or for Amazon Linux 2023:
sudo dnf install redis -y
```

2. **Configure Redis:**
```bash
sudo nano /etc/redis/redis.conf

# Key configurations:
bind 0.0.0.0                    # Bind to all interfaces
requirepass your_strong_password # Set password
maxmemory 512mb                 # Set memory limit
maxmemory-policy allkeys-lru    # Memory eviction policy
save 900 1                      # Persistence settings
logfile /var/log/redis/redis-server.log
```

3. **Start Redis Service:**
```bash
sudo systemctl start redis
sudo systemctl enable redis
sudo systemctl status redis
```

4. **Configure Security Group:**
- Add inbound rule: Custom TCP, Port 6379
- Source: Your application server's private IP only
- **Never use 0.0.0.0/0 for Redis in production**

5. **Test Connection:**
```bash
redis-cli -h localhost -p 6379 -a your_password ping
```

6. **Update Environment Variables:**
Create `.env` file with your EC2 Redis configuration:
```env
REDIS_HOST=172.31.x.x  # Your EC2 private IP
REDIS_PASSWORD=your_strong_password
```

### Deployment Commands on EC2:
```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Option A: Quick start with screen/tmux (development)
screen -S celery-worker
python -m celery -A configurations worker --loglevel=INFO

# New screen session
screen -S celery-beat
python -m celery -A configurations beat --loglevel=INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Production Systemd Setup:
```bash
# Copy service files
sudo cp deployment/celery-worker.service /etc/systemd/system/
sudo cp deployment/celery-beat.service /etc/systemd/system/

# Update paths in service files
sudo nano /etc/systemd/system/celery-worker.service  # Update paths
sudo nano /etc/systemd/system/celery-beat.service    # Update paths

# Reload systemd and start services
sudo systemctl daemon-reload
sudo systemctl enable celery-worker celery-beat
sudo systemctl start celery-worker celery-beat

# Check status
sudo systemctl status celery-worker
sudo systemctl status celery-beat

# View logs
sudo journalctl -u celery-worker -f
sudo journalctl -u celery-beat -f
```

## 📊 Production Considerations

1. **Redis Persistence**: Configure Redis with appropriate persistence settings
2. **Worker Scaling**: Use multiple workers for high throughput
3. **Monitoring**: Consider Flower for advanced monitoring
4. **Queues**: Separate critical and non-critical tasks into different queues
5. **Error Handling**: Implement proper error handling and alerting
6. **Security**: Secure Redis instance and use proper authentication
7. **Process Management**: Use systemd services for production deployment
8. **Load Balancing**: Use multiple worker instances behind a load balancer

## 🎯 Next Steps

- Set up Flower for advanced monitoring
- Implement task result storage optimization
- Add more sophisticated task routing
- Set up production-grade Redis configuration
- Implement task priority queues
- Add comprehensive error alerting

The system is now production-ready with proper error handling, retry policies, and multi-tenant support! 