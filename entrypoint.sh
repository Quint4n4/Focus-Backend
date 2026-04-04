#!/bin/sh
set -e

echo "==> Aplicando migraciones..."
python manage.py migrate --no-input

echo "==> Creando superadmin si no existe..."
python manage.py shell -c "
from apps.authentication.models import User
if not User.objects.filter(email='admin@focus.com').exists():
    User.objects.create_superuser(
        email='admin@focus.com',
        password='Admin123!',
        first_name='Super',
        last_name='Admin',
        role='super_admin',
    )
    print('Superadmin creado.')
else:
    print('Superadmin ya existe.')
"

echo "==> Iniciando gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
