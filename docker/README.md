# Docker Deployment Guide for Redis and Celery

This guide provides multiple Docker deployment options for Redis and Celery with your Django application.

## 🚀 Quick Start Options

### Option 1: All-in-One Docker Compose (Recommended)

Use the main `docker-compose.yml` file that includes all services:

```bash
# Update the passwords in docker-compose.yml first
# Then start all services
docker-compose up -d

# View logs
docker-compose logs -f celery-worker
docker-compose logs -f celery-beat
```

### Option 2: Separate Services (Flexible)

Start services separately for more control:

```bash
# 1. Create network
docker network create tenmil-network

# 2. Start Redis
cd docker
docker-compose -f redis.yml up -d

# 3. Start your Django app (connect to tenmil-network)
# Add this to your existing Django container config:
# networks:
#   - tenmil-network

# 4. Start Celery services
docker-compose -f celery.yml up -d
```

### Option 3: Individual Containers

```bash
# 1. Start Redis
docker run -d \
  --name tenmil-redis \
  --network tenmil-network \
  -p 6379:6379 \
  redis:7-alpine redis-server --requirepass your_strong_password

# 2. Start Celery Worker
docker run -d \
  --name tenmil-celery-worker \
  --network tenmil-network \
  -v $(pwd):/app \
  -w /app \
  -e REDIS_HOST=tenmil-redis \
  -e REDIS_PASSWORD=your_strong_password \
  your-django-image \
  python -m celery -A configurations worker --loglevel=INFO

# 3. Start Celery Beat
docker run -d \
  --name tenmil-celery-beat \
  --network tenmil-network \
  -v $(pwd):/app \
  -w /app \
  -e REDIS_HOST=tenmil-redis \
  -e REDIS_PASSWORD=your_strong_password \
  your-django-image \
  python -m celery -A configurations beat --loglevel=INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## 🔧 Configuration

### Environment Variables

Set these in your container environment or `.env` file:

```env
REDIS_HOST=redis  # or tenmil-redis for individual containers
REDIS_PORT=6379
REDIS_PASSWORD=your_strong_password_here
REDIS_DB=0
```

### Update Docker Compose Files

1. **Replace passwords**: Change `your_strong_password_here` to a strong password
2. **Update image names**: Replace build contexts with your actual image if using pre-built images
3. **Adjust volumes**: Ensure volume mounts match your project structure
4. **Configure networks**: Make sure all services use the same network

## 📊 Monitoring

### Flower (Celery Monitoring)

Access Flower web interface at `http://localhost:5555` to monitor:
- Active workers
- Task queues
- Task history
- Worker statistics

### Redis Commander (Redis Web UI)

Access Redis Commander at `http://localhost:8081` to:
- Browse Redis data
- Monitor memory usage
- Execute Redis commands

### Docker Logs

```bash
# View all Celery logs
docker-compose logs -f celery-worker celery-beat

# View Redis logs
docker-compose logs -f redis

# View specific container logs
docker logs tenmil-celery-worker -f
```

## 🛠️ Common Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart Celery services only
docker-compose restart celery-worker celery-beat

# Scale workers
docker-compose up -d --scale celery-worker=3

# View running containers
docker ps

# Execute commands in containers
docker exec -it tenmil-celery-worker bash
docker exec -it tenmil-redis redis-cli -a your_password
```

## 🚨 Troubleshooting

### Container Issues
```bash
# Check container status
docker ps -a

# View container logs
docker logs container-name

# Restart specific service
docker-compose restart service-name
```

### Redis Connection Issues
```bash
# Test Redis connection from another container
docker exec -it tenmil-celery-worker redis-cli -h redis -p 6379 -a your_password ping

# Check network connectivity
docker exec -it tenmil-celery-worker ping redis
```

### Celery Issues
```bash
# Check Celery worker status
docker exec -it tenmil-celery-worker celery -A configurations inspect active

# Check Celery beat schedule
docker exec -it tenmil-celery-beat celery -A configurations inspect scheduled
```

## 🔒 Production Considerations

1. **Use secrets management** instead of plain text passwords
2. **Configure Redis persistence** with volume mounts
3. **Set up proper logging** with log drivers
4. **Use health checks** in Docker Compose
5. **Configure resource limits** for containers
6. **Set up monitoring** with Prometheus/Grafana
7. **Use multi-stage builds** to reduce image size
8. **Configure proper networks** with firewall rules

## 🎯 Expected Results

Once running, you should see:
- ✅ Error logs every 30 seconds from the scheduled task
- ✅ API endpoints working at `/v1/api/tasks/`
- ✅ Flower monitoring at `http://localhost:5555`
- ✅ Redis Commander at `http://localhost:8081`
- ✅ Django admin showing periodic tasks 