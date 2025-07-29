#!/bin/bash

# Quick start script for Redis and Celery with Docker
# Usage: ./docker/start-celery.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐳 Starting Redis and Celery with Docker...${NC}"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Generating secure Redis password...${NC}"
REDIS_PASSWORD=$(openssl rand -base64 32)

echo -e "${YELLOW}🔧 Creating Docker network...${NC}"
docker network create tenmil-network 2>/dev/null || echo "Network already exists"

echo -e "${YELLOW}🚀 Starting Redis container...${NC}"
docker run -d \
  --name tenmil-redis \
  --network tenmil-network \
  -p 6379:6379 \
  -v redis_data:/data \
  --restart unless-stopped \
  redis:7-alpine redis-server --requirepass "${REDIS_PASSWORD}"

# Wait for Redis to be ready
echo -e "${YELLOW}⏳ Waiting for Redis to be ready...${NC}"
sleep 3

# Test Redis connection
if docker exec tenmil-redis redis-cli -a "${REDIS_PASSWORD}" ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is running successfully${NC}"
else
    echo -e "${RED}❌ Redis failed to start${NC}"
    exit 1
fi

echo -e "${YELLOW}🔨 Building Django image (if needed)...${NC}"
docker build -t tenmil-app .

echo -e "${YELLOW}👷 Starting Celery Worker...${NC}"
docker run -d \
  --name tenmil-celery-worker \
  --network tenmil-network \
  -v $(pwd):/app \
  -w /app \
  -e REDIS_HOST=tenmil-redis \
  -e REDIS_PORT=6379 \
  -e REDIS_PASSWORD="${REDIS_PASSWORD}" \
  -e REDIS_DB=0 \
  -e DJANGO_SETTINGS_MODULE=configurations.settings \
  --restart unless-stopped \
  tenmil-app \
  python -m celery -A configurations worker --loglevel=INFO --concurrency=4

echo -e "${YELLOW}⏰ Starting Celery Beat...${NC}"
docker run -d \
  --name tenmil-celery-beat \
  --network tenmil-network \
  -v $(pwd):/app \
  -w /app \
  -e REDIS_HOST=tenmil-redis \
  -e REDIS_PORT=6379 \
  -e REDIS_PASSWORD="${REDIS_PASSWORD}" \
  -e REDIS_DB=0 \
  -e DJANGO_SETTINGS_MODULE=configurations.settings \
  --restart unless-stopped \
  tenmil-app \
  python -m celery -A configurations beat --loglevel=INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler

echo -e "${YELLOW}🌸 Starting Flower (Celery monitoring)...${NC}"
docker run -d \
  --name tenmil-flower \
  --network tenmil-network \
  -p 5555:5555 \
  -v $(pwd):/app \
  -w /app \
  -e REDIS_HOST=tenmil-redis \
  -e REDIS_PORT=6379 \
  -e REDIS_PASSWORD="${REDIS_PASSWORD}" \
  -e REDIS_DB=0 \
  --restart unless-stopped \
  tenmil-app \
  python -m celery -A configurations flower --broker="redis://:${REDIS_PASSWORD}@tenmil-redis:6379/0"

# Wait a moment for services to start
sleep 3

echo -e "${GREEN}🎉 All services started successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Service Information:${NC}"
echo -e "${YELLOW}Redis:${NC}               Running on port 6379"
echo -e "${YELLOW}Celery Worker:${NC}       Processing tasks"
echo -e "${YELLOW}Celery Beat:${NC}         Scheduling periodic tasks"
echo -e "${YELLOW}Flower:${NC}              http://localhost:5555"
echo ""
echo -e "${BLUE}🔐 Redis Configuration:${NC}"
echo "REDIS_HOST=localhost  # or tenmil-redis from within containers"
echo "REDIS_PORT=6379"
echo "REDIS_PASSWORD=${REDIS_PASSWORD}"
echo "REDIS_DB=0"
echo ""
echo -e "${BLUE}🛠️  Useful Commands:${NC}"
echo "docker logs tenmil-celery-worker -f     # View worker logs"
echo "docker logs tenmil-celery-beat -f       # View beat logs"
echo "docker logs tenmil-redis -f             # View Redis logs"
echo "docker exec -it tenmil-redis redis-cli -a '${REDIS_PASSWORD}' ping  # Test Redis"
echo ""
echo -e "${GREEN}✅ Your error logging task will start automatically every 30 seconds!${NC}"
echo -e "${YELLOW}🔍 Check the worker logs to see it in action:${NC}"
echo "docker logs tenmil-celery-worker -f" 