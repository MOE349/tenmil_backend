#!/bin/sh
set -e

echo "upgrade pip"
python3 -m pip install --upgrade pip
echo "installing requirements"
python3 -m pip install -r requirements.txt

echo "creating database makemigrations"
python3 manage.py makemigrations --noinput

echo "creating database migrate"
python3 manage.py migrate --noinput

echo "collect statics"
python3 manage.py collectstatic --noinput

echo "Starting Server..."
export DJANGO_SETTINGS_MODULE=configurations.settings
export DJANGO_CONFIGURATION=Production  # or Dev, Staging, etc.
exec gunicorn configurations.wsgi:application --bind 0.0.0.0:8000

