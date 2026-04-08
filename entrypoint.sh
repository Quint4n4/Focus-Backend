#!/bin/sh

echo "==> Aplicando migraciones..."
if python manage.py migrate --no-input; then
    echo "==> Migraciones aplicadas correctamente."
else
    echo "!!! WARN: migrate falló — arrancando gunicorn de todas formas para que /health/ sea accesible."
fi

echo "==> Recopilando archivos estáticos..."
python manage.py collectstatic --no-input || echo "!!! WARN: collectstatic falló."

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
" || echo "!!! WARN: creación de superadmin falló (DB no disponible)."

echo "==> Iniciando gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
