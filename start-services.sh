#!/bin/bash

# Start all services using your existing Docker setup
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting Django app with Redis and Celery...${NC}"

# Generate a secure password if not set
if [ -z "$REDIS_PASSWORD" ]; then
    REDIS_PASSWORD=$(openssl rand -base64 32)
    echo -e "${YELLOW}Generated Redis password: ${REDIS_PASSWORD}${NC}"
    echo "REDIS_PASSWORD=${REDIS_PASSWORD}" >> .env
fi

echo -e "${YELLOW}📦 Building and starting all services...${NC}"

# Replace placeholder password in docker-compose.yml
sed -i "s/your_strong_password_here/${REDIS_PASSWORD}/g" docker-compose.yml

# Start all services
docker-compose up -d

echo -e "${GREEN}✅ All services started!${NC}"
echo ""
echo -e "${BLUE}📋 Service Status:${NC}"
docker-compose ps

echo ""
echo -e "${BLUE}🔍 Monitor your services:${NC}"
echo "Web app:       http://localhost:8000"
echo "Flower:        http://localhost:5555"
echo "Worker logs:   docker-compose logs -f celery-worker"
echo "Beat logs:     docker-compose logs -f celery-beat"
echo "All logs:      docker-compose logs -f"

echo ""
echo -e "${GREEN}🎉 Your 30-second error logging task is now running!${NC}"
echo -e "${YELLOW}View it in action:${NC} docker-compose logs -f celery-worker" 