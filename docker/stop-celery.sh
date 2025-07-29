#!/bin/bash

# Stop and cleanup script for Redis and Celery Docker containers
# Usage: ./docker/stop-celery.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Stopping Redis and Celery Docker containers...${NC}"

# Stop containers
echo -e "${YELLOW}📦 Stopping containers...${NC}"
docker stop tenmil-redis tenmil-celery-worker tenmil-celery-beat tenmil-flower 2>/dev/null || true

# Remove containers
echo -e "${YELLOW}🗑️  Removing containers...${NC}"
docker rm tenmil-redis tenmil-celery-worker tenmil-celery-beat tenmil-flower 2>/dev/null || true

# Optional: Remove network (uncomment if you want to clean up completely)
# echo -e "${YELLOW}🌐 Removing network...${NC}"
# docker network rm tenmil-network 2>/dev/null || true

# Optional: Remove Redis data volume (uncomment if you want to clean up data)
# echo -e "${YELLOW}💾 Removing Redis data volume...${NC}"
# docker volume rm redis_data 2>/dev/null || true

echo -e "${GREEN}✅ All Celery and Redis containers stopped and removed!${NC}"
echo ""
echo -e "${BLUE}📋 Cleanup Summary:${NC}"
echo "- Stopped: Redis, Celery Worker, Celery Beat, Flower"
echo "- Removed: All containers"
echo "- Kept: Network (tenmil-network) and Redis data volume"
echo ""
echo -e "${YELLOW}💡 To restart everything:${NC}"
echo "./docker/start-celery.sh" 