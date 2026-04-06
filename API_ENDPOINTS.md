# Focus API — Endpoints

Base URL: `https://focus-backend-u211p.sevalla.app`

---

## Utilidades

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET`  | `/health/` | Health check del servidor |
| `*`    | `/admin/`  | Panel de administración Django |

---

## Autenticación — `/api/auth/`

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/auth/login/` | Login con email + password |
| `POST` | `/api/auth/logout/` | Cerrar sesión (blacklist del refresh token) |
| `POST` | `/api/auth/refresh/` | Renovar access token |
| `GET`  | `/api/auth/me/` | Datos del usuario autenticado |
| `POST` | `/api/auth/biometric/enable/` | Activar login biométrico |
| `POST` | `/api/auth/biometric/disable/` | Desactivar login biométrico |
| `POST` | `/api/auth/biometric/login/` | Login con biométrico |
| `POST` | `/api/auth/onboarding/complete/` | Marcar onboarding como completado |

---

## Usuarios — `/api/users/`

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/users/` | Listar usuarios |
| `GET / PATCH / DELETE` | `/api/users/{uuid}/` | Detalle, editar o eliminar usuario |
| `POST` | `/api/users/invite/` | Crear link de invitación |
| `GET` | `/api/users/invite/verify/` | Verificar token de invitación |
| `POST` | `/api/users/accept-invite/` | Aceptar invitación y registrarse |

---

## Áreas — `/api/areas/`

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET / POST` | `/api/areas/` | Listar / crear área |
| `GET / PATCH / DELETE` | `/api/areas/{uuid}/` | Detalle, editar o eliminar área |
| `GET / POST / DELETE` | `/api/areas/{uuid}/members/` | Ver / agregar / quitar miembros |

---

## Actividades — `/api/activities/`

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET / POST` | `/api/activities/` | Listar / crear actividad |
| `GET / PATCH / DELETE` | `/api/activities/{uuid}/` | Detalle, editar o eliminar |
| `POST` | `/api/activities/{uuid}/move/` | Cambiar estado (`inbox → today → pending → completed`) |
| `POST` | `/api/activities/{uuid}/assign/` | Asignar actividad a un usuario |
| `POST` | `/api/activities/{uuid}/complete/` | Marcar como completada |
| `GET / POST` | `/api/activities/{uuid}/attachments/` | Ver / subir adjuntos |
| `DELETE` | `/api/activities/{uuid}/attachments/{uuid}/` | Eliminar adjunto |
| `GET` | `/api/activities/{uuid}/logs/` | Historial / audit log de la actividad |

---

## Proyectos — `/api/projects/`

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET / POST` | `/api/projects/` | Listar / crear proyecto |
| `GET / PATCH / DELETE` | `/api/projects/{uuid}/` | Detalle, editar o eliminar |
| `GET` | `/api/projects/{uuid}/activities/` | Actividades del proyecto |
| `GET` | `/api/projects/{uuid}/progress/` | Progreso del proyecto (%) |

---

## Estadísticas — `/api/stats/`

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/stats/personal/` | Stats del usuario autenticado |
| `GET` | `/api/stats/global/` | Stats globales (solo admins) |
| `GET` | `/api/stats/workers/` | Stats por trabajador |
| `GET` | `/api/stats/area/{uuid}/` | Stats de un área específica |
| `GET` | `/api/stats/drilldown/` | Drill-down detallado |

---

## Estados de actividades

```
inbox → today | tomorrow | scheduled → pending → completed
```

## Roles

| Rol | Valor |
|-----|-------|
| Super Administrador | `super_admin` |
| Administrador de Área | `admin_area` |
| Trabajador | `trabajador` |
