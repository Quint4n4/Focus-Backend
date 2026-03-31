# Plan de Tests de Endpoints

Objetivo: validar comportamiento funcional, permisos y seguridad de toda la API REST.

## 1) Alcance

Modulos:
- Auth
- Users
- Areas
- Activities
- Projects
- Stats

Ambientes:
- Local con DB limpia.
- Opcional: entorno staging con configuracion de produccion.

## 2) Matriz base endpoint x rol

Roles a probar:
- `super_admin`
- `admin_area`
- `trabajador`
- `anonimo` (solo endpoints publicos)

Criterio minimo:
- cada endpoint con al menos 1 caso exitoso y 1 caso de rechazo por permiso.

## 3) Capas de prueba

### 3.1 Smoke tests (prioridad alta)

Validar rapidamente:
- `POST /api/auth/login/` (200 credenciales validas, 401 invalidas)
- `GET /api/auth/me/` (401 sin token, 200 con token)
- `GET /api/activities/` (200 con token)
- `GET /api/stats/personal/` (200 con token)

### 3.2 Funcionales por modulo

- Auth: login/logout/refresh/biometrico/onboarding.
- Users: listado, detalle, update propio, invitacion y aceptacion.
- Areas: CRUD y miembros.
- Activities: CRUD, move, assign, complete, adjuntos y logs.
- Projects: CRUD, activities, progress.
- Stats: personal, area, drilldown con filtros.

### 3.3 Permisos (RBAC y alcance)

- `trabajador` no puede:
  - crear areas;
  - invitar usuarios;
  - editar/eliminar proyectos.
- `admin_area` no puede operar fuera de su area.
- `super_admin` puede operar globalmente.

### 3.4 Seguridad

- JWT:
  - refresh rota token y blacklistea anterior;
  - logout invalida refresh.
- Rate limiting:
  - login devuelve `429` tras exceder limite;
  - invite devuelve `429` tras exceder limite.
- Brute force:
  - Axes bloquea despues de intentos fallidos configurados.
- Aislamiento:
  - acceso cross-area devuelve `403` o `404` segun endpoint.

### 3.5 Integridad de dominio

- Flujo de estados de actividad via `/move/`.
- `/complete/` fija `status=completed` y `completed_at`.
- Auditoria:
  - eventos `created/updated/deleted` por signal;
  - eventos `moved/assigned/completed` por vistas.

## 4) Datos de prueba (fixtures sugeridos)

- 2 areas (`A1`, `A2`).
- 1 `super_admin`.
- 2 `admin_area` (uno por area).
- 3 `trabajador` (2 en `A1`, 1 en `A2`).
- Proyectos y actividades en ambas areas.
- Invitacion vigente y otra expirada.

## 5) Ejecucion

Comandos base:
```bash
python manage.py test
python manage.py test apps.authentication
python manage.py test apps.users
python manage.py test apps.areas
python manage.py test apps.activities
python manage.py test apps.projects
python manage.py test apps.stats
```

Opcional con `pytest` si esta habilitado:
```bash
pytest -v
```

## 6) Criterios de aceptacion

- 100% de endpoints documentados con pruebas asociadas.
- Todos los casos de permisos criticos cubiertos.
- Casos negativos obligatorios cubiertos: `401`, `403`, `404`, `429`.
- No regresiones en flujo JWT (login/refresh/logout).
