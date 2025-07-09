#!/bin/sh
set -e

echo "upgrade pip"
python3 -m pip install --upgrade pip
echo "installing requirements"
python3 -m pip install -r requirements.txt

export DJANGO_SETTINGS_MODULE=configurations.settings
export DJANGO_CONFIGURATION=Production  # or Dev, Staging, etc.

echo "creating database makemigrations"
python3 manage.py makemigrations --noinput

echo "creating database migrate"
python3 manage.py migrate --noinput

echo "collect statics"
python3 manage.py collectstatic --noinput

echo "Starting Server..."
exec python manage.py runserver 0.0.0.0:8000 --noinput

