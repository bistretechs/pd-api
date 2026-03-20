#!/bin/bash
set -e

python manage.py collectstatic --noinput
python manage.py migrate django_celery_results --fake
python manage.py migrate --noinput

exec gunicorn client.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120
