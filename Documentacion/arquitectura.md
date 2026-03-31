# Arquitectura del Backend

## Stack tecnológico

| Componente | Tecnología | Versión |
|---|---|---|
| Framework web | Django | 5.0+ |
| API REST | Django REST Framework | 3.15+ |
| Autenticación | djangorestframework-simplejwt | 5.3+ |
| Base de datos | PostgreSQL | 15 |
| Caché / Rate limiting | Redis | 7 |
| Protección brute-force | django-axes | 6.4+ |
| Rate limiting por endpoint | django-ratelimit | 4.1+ |
| CORS | django-cors-headers | 4.3+ |
| CSP (producción) | django-csp | 3.8+ |
| Servidor WSGI | Gunicorn | 21+ |
| Proxy reverso | Nginx | 1.25 Alpine |
| Contenedores | Docker + Docker Compose | 3.9 |
| Monitoreo errores | Sentry SDK | 1.40+ |

## Estructura del proyecto

```
Focus-dev/
├── config/
│   ├── settings/
│   │   ├── base.py         # Configuración compartida (JWT, DRF, logging, CORS)
│   │   ├── local.py        # Desarrollo: DEBUG=True, axes desactivado, SQLite fallback
│   │   └── production.py   # Producción: SSL, HSTS, CSP, Sentry
│   ├── urls.py             # Router principal
│   └── wsgi.py
│
├── apps/
│   ├── authentication/     # Usuario personalizado + JWT + biométrico
│   ├── users/              # Gestión de usuarios + sistema de invitaciones
│   ├── areas/              # Contenedores de departamento/equipo
│   ├── activities/         # Tareas con 6 estados + audit log + adjuntos
│   ├── projects/           # Colecciones de actividades con seguimiento
│   └── stats/              # Analytics: personal, área, drill-down
│
├── core/
│   ├── permissions.py      # Clases de permisos por rol
│   ├── exceptions.py       # Handler de errores (incluye 429 para ratelimit)
│   └── pagination.py       # Paginación estándar (20 items/página)
│
├── nginx/
│   ├── nginx.conf          # Configuración de producción con rate limiting
│   └── ssl/                # Certificados TLS (gitignoreados)
│
├── requirements/
│   ├── base.txt            # Dependencias comunes
│   ├── local.txt           # + debug toolbar
│   └── production.txt      # + django-csp, sentry-sdk
│
├── Dockerfile
├── docker-compose.yml              # Desarrollo
├── docker-compose.production.yml   # Producción (+ Nginx)
└── .env.example
```

## Apps y responsabilidades

### `apps/authentication`
Gestiona la identidad. Contiene el modelo `User` personalizado (extiende `AbstractBaseUser`), el `UserManager` sin username, y todas las vistas JWT. Es la única app que maneja tokens.

### `apps/users`
Gestiona el ciclo de vida de usuarios dentro del sistema. Contiene el modelo `Invitation` con tokens hasheados (SHA-256) para el flujo de registro sin email.

### `apps/areas`
Representa los departamentos o equipos. Cada usuario pertenece a un área (excepto super_admin que no tiene área). Las áreas son el principal delimitador de visibilidad de datos.

### `apps/activities`
El núcleo del sistema. Contiene el modelo `Activity` con 6 estados, `ActivityLog` para auditoría automática via Django signals, y `ActivityAttachment` para archivos adjuntos.

### `apps/projects`
Agrupa actividades en colecciones con seguimiento de progreso. Los proyectos pertenecen a un área.

### `apps/stats`
Sin modelos propios. Vistas de solo lectura que ejecutan consultas de agregación ORM sobre actividades. Tres niveles: personal, área, drill-down con filtros.

### `core`
Módulo transversal. Contiene permisos reutilizables, el handler de excepciones y la clase de paginación.

## Decisiones de diseño clave

### UUID como clave primaria
Todos los modelos usan `UUIDField` como PK. Previene la enumeración de IDs secuenciales (un atacante no puede adivinar `id=2` si el anterior fue `id=1`).

### Modelo User personalizado
El campo `USERNAME_FIELD = 'email'` elimina el campo `username`. Se extiende `AbstractBaseUser` para tener control total sobre el modelo desde el inicio del proyecto (cambiarlo después requeriría recrear toda la base de datos).

### Separación de settings
Tres archivos de configuración en cascada (`base.py` → `local.py` / `production.py`). La variable `DJANGO_SETTINGS_MODULE` selecciona cuál usar. Permite comportamientos radicalmente distintos entre entornos sin código condicional.

### Audit log automático via signals
El modelo `ActivityLog` se llena automáticamente mediante `post_save` y `pre_delete` sobre `Activity`. Las vistas no necesitan código de logging explícito. Las vistas pasan el usuario actuante via `instance._updated_by` antes de guardar.

### Tokens de invitación hasheados
El token real nunca se almacena en base de datos. Solo se guarda su hash SHA-256. Si la tabla `users_invitation` fuera comprometida, los tokens son inútiles sin el valor original.

### JWT con rotación obligatoria
`ROTATE_REFRESH_TOKENS = True` y `BLACKLIST_AFTER_ROTATION = True` aseguran que cada uso de un refresh token genera uno nuevo e invalida el anterior. Un refresh token robado solo puede usarse una vez antes de quedar en la blacklist.

### Dos claves secretas separadas
`SECRET_KEY` (Django general) y `JWT_SECRET_KEY` (firma de tokens) son independientes. Rotar una no invalida la otra.

## Flujo de autenticación

```
Cliente                          Servidor
  │                                  │
  ├─ POST /api/auth/login/ ─────────►│
  │   {email, password}              │ Valida credenciales
  │◄────────────────────────────────┤
  │   {access (15min), refresh (7d)} │
  │                                  │
  ├─ GET /api/... ──────────────────►│
  │   Authorization: Bearer <access> │ Valida JWT
  │◄────────────────────────────────┤
  │   {datos}                        │
  │                                  │
  │   (access expirado)              │
  ├─ POST /api/auth/refresh/ ───────►│
  │   {refresh: <token>}             │ Valida, blacklistea el anterior
  │◄────────────────────────────────┤
  │   {access (nuevo), refresh (nuevo)} │
```

## Flujo de invitación

```
Admin                            Servidor                         Nuevo usuario
  │                                  │                                 │
  ├─ POST /api/users/invite/ ───────►│                                 │
  │   {area, role}                   │ Genera token aleatorio          │
  │                                  │ Guarda hash SHA-256             │
  │◄────────────────────────────────┤                                 │
  │   {token: <raw>, expires_at}     │                                 │
  │                                  │                                 │
  │   Comparte el token por          │                                 │
  │   cualquier canal seguro ──────────────────────────────────────►  │
  │                                  │                                 │
  │                                  │◄── POST /api/users/accept-invite/
  │                                  │    {token, email, first_name,  │
  │                                  │     last_name, password}       │
  │                                  │ Hashea token, busca en DB      │
  │                                  │ Verifica no expirado ni usado  │
  │                                  │ Crea usuario                   │
  │                                  ├────────────────────────────────►
  │                                  │    {id, email, role}           │
```

## Flujo de estados de actividad

```
INBOX ──────┬──► TODAY
            ├──► TOMORROW
            ├──► SCHEDULED
            └──► (directo a) PENDING
                      │
                      ▼
                  COMPLETED
```

Los cambios de estado se realizan via `PATCH /api/activities/<pk>/move/` y quedan registrados automáticamente en `ActivityLog`.

## Modelo de permisos por recurso

| Recurso | Crear | Leer | Actualizar | Eliminar |
|---|---|---|---|---|
| Área | super_admin | todos | super_admin | super_admin |
| Miembros de área | — | propio área | — | — |
| Usuario | accept-invite (público) | admin+ | propio / admin+ | — |
| Invitación | admin_area+ | — | — | — |
| Actividad | trabajador+ | propias/área/todo | propias/área/todo | propias/área/todo |
| Proyecto | admin_area+ | propio área | admin_area+ | admin_area+ |
| Stats personal | — | propio | — | — |
| Stats área | — | admin_area+ | — | — |
| Stats drilldown | — | admin_area+ | — | — |
