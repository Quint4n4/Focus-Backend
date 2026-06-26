#!/bin/sh

echo "==> Aplicando migraciones..."
if python manage.py migrate --no-input; then
    echo "==> Migraciones aplicadas correctamente."
else
    echo "!!! WARN: migrate falló — arrancando gunicorn de todas formas para que /health/ sea accesible."
fi

echo "==> Recopilando archivos estáticos..."
python manage.py collectstatic --no-input || echo "!!! WARN: collectstatic falló."

echo "==> Creando admin de plataforma si no existe..."
python manage.py shell -c "
import os
from apps.authentication.models import User
email    = os.environ.get('PLATFORM_ADMIN_EMAIL',    'admin@focus.com')
password = os.environ.get('PLATFORM_ADMIN_PASSWORD', '')
if not password:
    print('WARN: PLATFORM_ADMIN_PASSWORD no definido — saltando creacion de admin.')
elif not User.objects.filter(email=email, is_staff=True).exists():
    User.objects.create_superuser(
        email=email,
        password=password,
        first_name='Platform',
        last_name='Admin',
        role='super_admin',
        company=None,
    )
    print('Admin de plataforma creado: ' + email)
else:
    print('Admin de plataforma ya existe: ' + email)
" || echo "!!! WARN: creacion de admin de plataforma fallo (DB no disponible)."

echo "==> Iniciando gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${GUNICORN_WORKERS:-3} \
    --timeout 120 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile -
