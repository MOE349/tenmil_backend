#!/bin/sh
set -e

echo "🚀 Starting Celery Worker..."

echo "upgrade pip"
python3 -m pip install --upgrade pip
echo "installing requirements"
python3 -m pip install -r requirements.txt

export DJANGO_SETTINGS_MODULE=configurations.settings
export DJANGO_CONFIGURATION=Production

# echo "⏳ Waiting for database to be ready..."
# python3 manage.py migrate --check

# echo "🔄 Running migrations (if needed)..."
# python3 manage.py migrate --noinput

echo "👷 Starting Celery Worker..."
exec python3 -m celery -A configurations worker --loglevel=INFO --concurrency=4 