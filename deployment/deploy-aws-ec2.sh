#!/bin/bash

# AWS EC2 Redis and Celery Deployment Script
# Run this script on your EC2 instance as ec2-user

set -e  # Exit on any error

echo "🚀 Starting AWS EC2 Redis and Celery deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as ec2-user
if [ "$USER" != "ec2-user" ]; then
    echo -e "${RED}❌ This script should be run as ec2-user${NC}"
    exit 1
fi

echo -e "${YELLOW}📦 Updating system packages...${NC}"
sudo yum update -y

echo -e "${YELLOW}📦 Installing Redis...${NC}"
if ! command -v redis-server &> /dev/null; then
    sudo yum install redis -y || sudo dnf install redis -y
    echo -e "${GREEN}✅ Redis installed successfully${NC}"
else
    echo -e "${GREEN}✅ Redis already installed${NC}"
fi

echo -e "${YELLOW}🔧 Configuring Redis...${NC}"
# Backup original config
sudo cp /etc/redis/redis.conf /etc/redis/redis.conf.backup

# Create Redis configuration
sudo tee /etc/redis/redis.conf > /dev/null <<EOF
bind 0.0.0.0
port 6379
timeout 0
keepalive 300
tcp-backlog 511
tcp-keepalive 60
tcp-user-timeout 0

# Security
requirepass $(openssl rand -base64 32)

# Memory
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000
rdbcompression yes
rdbchecksum yes
dbfilename dump.rdb
dir /var/lib/redis/

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log
syslog-enabled no
EOF

# Create log directory
sudo mkdir -p /var/log/redis
sudo chown redis:redis /var/log/redis

echo -e "${YELLOW}🚀 Starting Redis service...${NC}"
sudo systemctl start redis
sudo systemctl enable redis

# Test Redis
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis is running successfully${NC}"
else
    echo -e "${RED}❌ Redis failed to start${NC}"
    exit 1
fi

echo -e "${YELLOW}📝 Redis setup complete!${NC}"
echo -e "${YELLOW}🔐 Generated Redis password saved in /etc/redis/redis.conf${NC}"
echo -e "${YELLOW}📋 Add these to your .env file:${NC}"
echo "REDIS_HOST=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)"
echo "REDIS_PASSWORD=$(grep requirepass /etc/redis/redis.conf | cut -d' ' -f2)"
echo "REDIS_PORT=6379"
echo "REDIS_DB=0"

echo -e "${GREEN}🎉 Redis deployment completed successfully!${NC}"
echo -e "${YELLOW}📖 Next steps:${NC}"
echo "1. Update your application's .env file with the Redis credentials above"
echo "2. Configure security group to allow port 6379 from your app server"
echo "3. Install your Django app dependencies and run migrations"
echo "4. Start Celery worker and beat services"

echo -e "${YELLOW}🔍 Useful commands:${NC}"
echo "sudo systemctl status redis       # Check Redis status"
echo "sudo journalctl -u redis -f       # View Redis logs"
echo "redis-cli ping                     # Test Redis connection"
echo "redis-cli -a PASSWORD ping         # Test with password" 