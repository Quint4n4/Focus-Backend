# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Proyecto

Focus es una app de productividad para equipos. Backend: Django REST Framework + PostgreSQL + Redis. Cliente móvil: Flutter. El blueprint completo de implementación está en `backend_guide (1).md`.

## Comandos

### Desarrollo local (venv)
```bash
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux/Mac
pip install -r requirements/local.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Docker (recomendado)
```bash
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose logs -f web
```

### Tests
```bash
python manage.py test                        # todos los tests
python manage.py test apps.authentication    # una sola app
pytest -v                                    # si pytest está configurado
pytest apps/authentication/tests/test_views.py::LoginViewTest  # test individual
```

### Comandos útiles
```bash
python manage.py shell_plus         # shell interactivo (django-extensions)
python manage.py generate_invite    # crear link de invitación (comando personalizado)
python manage.py collectstatic      # para producción
```

## Arquitectura

### Estructura de apps
```
focus/
├── config/
│   ├── settings/
│   │   ├── base.py       # configuración compartida
│   │   ├── local.py      # overrides de desarrollo
│   │   └── production.py # overrides de producción
│   ├── urls.py
│   └── wsgi.py
└── apps/
    ├── authentication/   # Modelo User personalizado, JWT login/logout/refresh/me, biométrico
    ├── users/            # Gestión de usuarios, invitaciones (sin email, token de 24h)
    ├── areas/            # Contenedores de departamento/equipo
    ├── activities/       # Tareas con 6 estados + audit log via signals + adjuntos
    ├── projects/         # Colecciones de actividades con seguimiento de progreso
    └── stats/            # Analytics: personal, por área, drill-down
```

### Decisiones de diseño clave
- **Modelo User personalizado** usa `email` como `USERNAME_FIELD` (no username). Siempre extender `AbstractBaseUser`.
- **UUID como PK** en todos los modelos — previene enumeración de IDs secuenciales.
- **Tres roles**: `SUPER_ADMIN`, `ADMIN_AREA`, `TRABAJADOR`. Permisos enforzados con clases DRF personalizadas en cada app.
- **Audit log de actividades** es automático via Django signals (`post_save`, `pre_delete` sobre `Activity`). Nunca escribir código manual de logging para eventos de actividades.
- **Tokens JWT**: access=15min, refresh=7días, rotación activada (el refresh anterior se blacklistea en cada uso). `JWT_SECRET_KEY` separado del `SECRET_KEY` de Django.
- **Autenticación biométrica** es solo del lado del cliente. El backend solo guarda `biometrics_enabled` + `device_id` en User; nunca procesa datos biométricos.
- **Sistema de invitaciones**: links con tiempo limitado (24h), sin email requerido. Token almacenado hasheado en DB.
- **Rate limiting**: dos capas — Nginx (conteo de requests) + Django (`django-ratelimit` por endpoint).
- **Settings divididos**: `DJANGO_SETTINGS_MODULE=config.settings.local` en dev, `config.settings.production` en prod.

### Estados de actividades (flujo)
`INBOX → TODAY | TOMORROW | SCHEDULED → PENDING → COMPLETED`
Almacenados como string choices: `inbox`, `today`, `tomorrow`, `scheduled`, `pending`, `completed`.

### Rutas base de la API
```
/api/auth/        login, refresh, logout, me, biometric/enable, biometric/disable
/api/users/       list, invite, detail, update
/api/areas/       CRUD, members
/api/activities/  CRUD, move (cambiar estado), assign, complete, attachments
/api/projects/    CRUD con agregación de actividades
/api/stats/       personal, area, drilldown
```

### Variables de entorno (nunca hardcodear)
`DJANGO_SECRET_KEY`, `JWT_SECRET_KEY`, `DEBUG`, `DATABASE_URL`, `REDIS_URL`, `CORS_ALLOWED_ORIGINS`

### Dependencias de seguridad
`djangorestframework-simplejwt`, `django-axes` (brute-force), `django-cors-headers`, `django-csp`, `django-ratelimit`
