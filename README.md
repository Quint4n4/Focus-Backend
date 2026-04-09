# Focus Backend (DRF + PostgreSQL + Redis)

Backend de **Focus**, una app de productividad para equipos, construido con **Django REST Framework** y autenticación JWT.

Este README concentra la documentación principal del proyecto para uso en desarrollo local, despliegue y operación.

---

## 1) Stack tecnológico

- **Lenguaje:** Python 3
- **Framework:** Django 5 + Django REST Framework
- **Base de datos:** PostgreSQL
- **Cache/colas ligeras:** Redis
- **Auth:** JWT (`djangorestframework-simplejwt`) + blacklist/rotación
- **Seguridad:** `django-axes`, `django-ratelimit`, `django-cors-headers`, `django-csp`
- **Servidor WSGI:** Gunicorn
- **Static files en producción:** WhiteNoise
- **Contenedores:** Docker / Docker Compose

Dependencias principales (`requirements/base.txt`):

- `django`
- `djangorestframework`
- `djangorestframework-simplejwt`
- `django-cors-headers`
- `django-ratelimit`
- `django-axes`
- `psycopg2-binary`
- `python-decouple`
- `dj-database-url`
- `redis`
- `gunicorn`
- `Pillow`
- `django-extensions`

Producción (`requirements/production.txt`):

- `django-csp`
- `sentry-sdk`
- `whitenoise[brotli]`

Desarrollo (`requirements/local.txt`):

- `django-debug-toolbar`

---

## 2) Arquitectura y módulos

Estructura principal:

- `config/` configuración global (settings, urls, wsgi/asgi)
- `apps/authentication/` usuarios, login/logout/refresh/me, biométrico
- `apps/users/` invitaciones y gestión de usuarios
- `apps/areas/` áreas/departamentos
- `apps/activities/` actividades, logs y adjuntos
- `apps/projects/` proyectos y progreso
- `apps/stats/` endpoints de estadísticas
- `core/` permisos, paginación y manejo de excepciones

Modelo de usuario personalizado:

- `AUTH_USER_MODEL = authentication.User`
- `USERNAME_FIELD = email`
- Roles: `super_admin`, `admin_area`, `trabajador`, `personal`
- PKs UUID en modelos de negocio

---

## 3) Configuración de entorno

Copiar `.env.example` a `.env` y completar valores.

Variables importantes:

- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS`
- `DATABASE_URL`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `REDIS_URL`
- `CORS_ALLOWED_ORIGINS`
- `DJANGO_SETTINGS_MODULE`

Settings por entorno:

- Local: `config.settings.local`
- Producción: `config.settings.production`

---

## 4) Ejecución local (venv)

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements/local.txt
python manage.py migrate
python manage.py runserver
```

Si necesitas superusuario manual:

```bash
python manage.py createsuperuser
```

---

## 5) Ejecución con Docker (desarrollo)

```bash
docker-compose up -d --build
docker-compose exec web python manage.py migrate
docker-compose logs -f web
```

Archivo usado: `docker-compose.yml`

---

## 6) Despliegue / producción

Archivos clave:

- `docker-compose.production.yml`
- `entrypoint.sh`
- `config/settings/production.py`

### Qué hace `entrypoint.sh` al iniciar:

1. Ejecuta migraciones (`python manage.py migrate --no-input`)
2. Ejecuta `collectstatic`
3. Crea superadmin por defecto si no existe
4. Inicia Gunicorn

Superadmin bootstrap automático:

- Email: `admin@focus.com`
- Password: `Admin123!`
- Role: `super_admin`

> Importante: cambiar esta credencial en entorno productivo real.

---

## 7) Migraciones

Aplicar todas:

```bash
python manage.py migrate
```

Crear migraciones nuevas:

```bash
python manage.py makemigrations
python manage.py migrate
```

Apps con migraciones activas en el proyecto:

- `authentication`
- `users`
- `areas`
- `activities`
- `projects`
- `token_blacklist`
- `axes`
- Django core apps (`auth`, `admin`, `sessions`, `contenttypes`)

---

## 8) Comandos útiles

```bash
python manage.py runserver
python manage.py shell_plus
python manage.py collectstatic --no-input
python manage.py test
python manage.py test apps.authentication
pytest -v
```

Con Docker:

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py test
docker-compose logs -f web
```

---

## 9) Endpoints (actualizados)

Base URL producción:

`https://focus-backend-u211p.sevalla.app`

### Sistema

- `GET /health/`
- `GET /admin/`

### Auth (`/api/auth/`)

- `POST /api/auth/login/`
- `POST /api/auth/logout/`
- `POST /api/auth/refresh/`
- `GET /api/auth/me/`
- `POST /api/auth/biometric/enable/`
- `POST /api/auth/biometric/disable/`
- `POST /api/auth/biometric/login/`
- `POST /api/auth/onboarding/complete/`

### Users (`/api/users/`)

- `GET /api/users/`
- `GET/PATCH /api/users/{uuid}/`
- `POST /api/users/invite/`
- `POST /api/users/invite/verify/`
- `POST /api/users/accept-invite/`

### Areas (`/api/areas/`)

- `GET/POST /api/areas/`
- `GET/PATCH/DELETE /api/areas/{uuid}/`
- `GET/POST/DELETE /api/areas/{uuid}/members/`

### Activities (`/api/activities/`)

- `GET/POST /api/activities/`
- `GET/PATCH/DELETE /api/activities/{uuid}/`
- `PATCH /api/activities/{uuid}/move/`
- `POST /api/activities/{uuid}/assign/`
- `POST /api/activities/{uuid}/complete/`
- `GET/POST /api/activities/{uuid}/attachments/`
- `GET /api/activities/{uuid}/attachments/{attachment_uuid}/file/`
- `DELETE /api/activities/{uuid}/attachments/{attachment_uuid}/`
- `GET /api/activities/{uuid}/logs/`

### Projects (`/api/projects/`)

- `GET/POST /api/projects/`
- `GET/PATCH/DELETE /api/projects/{uuid}/`
- `GET /api/projects/{uuid}/activities/`
- `GET /api/projects/{uuid}/progress/`

### Stats (`/api/stats/`)

- `GET /api/stats/personal/`
- `GET /api/stats/global/`
- `GET /api/stats/workers/`
- `GET /api/stats/area/{area_uuid}/`
- `GET /api/stats/drilldown/`

---

## 10) Roles y permisos (resumen)

- `super_admin`
  - Acceso completo
  - Puede invitar `super_admin`, `admin_area`, `trabajador`
- `admin_area`
  - Gestiona recursos de su área
  - No puede invitar `super_admin`
- `trabajador`
  - Acceso operativo de trabajo
  - Restricciones en acciones administrativas
- `personal`
  - Rol personal (uso individual), con alcance acotado

Permisos DRF custom en `core/permissions.py`:

- `IsSuperAdmin`
- `IsAdminAreaOrAbove`
- `IsWorkerOrAbove`
- `IsOwnerOrAssignee`
- `IsAreaMember`

---

## 11) Seguridad

Implementaciones relevantes:

- JWT con rotación y blacklist
- Límite de intentos con `django-axes`
- Rate limit por endpoint con `django-ratelimit`
- CORS controlado por variable de entorno
- CSP habilitado en producción
- HTTPS/HSTS en `production.py`
- Cookies seguras para sesión/CSRF en producción

---

## 12) Django Admin (tablas visibles)

Se dejó configurado para visualizar los modelos clave del sistema:

- Authentication
  - `User`
- Users
  - `Invitation`
- Areas
  - `Area`
- Projects
  - `Project`
- Activities
  - `Activity`
  - `ActivityLog`
  - `ActivityAttachment`

Archivos usados para registro en admin:

- `apps/authentication/admin.py`
- `apps/users/admin.py`
- `apps/areas/admin.py`
- `apps/projects/admin.py`
- `apps/activities/admin.py`

---

## 13) Diagnóstico y troubleshooting

### Error 404 en login desde app

Si la app llama `POST /auth/login/` dará 404.  
Ruta correcta: `POST /api/auth/login/`.

### Timeout inicial (30s) en app móvil

Puede ocurrir por cold start del servicio en plataforma cloud.  
Mitigaciones:

- subir `receiveTimeout` en cliente temporalmente
- mantener servicio caliente en proveedor

### `500` en endpoints (ej. `/api/projects/`, `/api/users/invite/`)

Un 500 es backend. Revisar logs del servidor con traceback (no solo access log).

Pasos recomendados:

1. Revisar logs de aplicación (error log)
2. Reproducir endpoint con mismo payload
3. Verificar estado de migraciones
4. Verificar datos corruptos/inconsistentes

### Admin sin estilos (404 `/static/admin/...`)

Verificar que `collectstatic` corrió y que WhiteNoise está activo en producción.

### Adjuntos no accesibles por URL de media

Confirmar estrategia de serving de media en producción (Nginx/S3/proxy) y permisos.

---

## 14) Estado funcional observado en pruebas recientes

- Login / refresh / logout funcionando
- Endpoints de actividades funcionando
- Endpoints de áreas y usuarios respondiendo
- Invitaciones y proyectos reportaron errores 500 en producción en algunos escenarios
- Se corrigió exposición de modelos en Django Admin para visibilidad operativa

---

## 15) Archivos de referencia del proyecto

- `API_ENDPOINTS.md` (lista operativa de endpoints)
- `BACKEND_PENDIENTES.md` (pendientes/bugs detectados en pruebas)
- `AREAS_AND_INVITE_FLOW.md` (flujo de áreas e invitaciones)
- `ROLES_VISIBILIDAD_Y_BACKEND.md` (reglas de visibilidad/roles)

---

## 16) Licencia

Definir según política del repositorio (MIT/privada/empresa).

