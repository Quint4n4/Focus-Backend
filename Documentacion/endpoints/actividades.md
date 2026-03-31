# Endpoints — Actividades

Base URL: `http://localhost:8000/api/activities/`

## Tabla rapida

| Metodo | Ruta | Auth | Roles |
|---|---|---|---|
| GET | `/` | Bearer | `super_admin`, `admin_area`, `trabajador` |
| POST | `/` | Bearer | `super_admin`, `admin_area`, `trabajador` |
| GET | `/<uuid:pk>/` | Bearer | segun acceso por area/owner/assignee |
| PATCH | `/<uuid:pk>/` | Bearer | segun acceso por area/owner/assignee |
| DELETE | `/<uuid:pk>/` | Bearer | `super_admin`, `admin_area` de area, o owner |
| PATCH | `/<uuid:pk>/move/` | Bearer | segun acceso por area/owner/assignee |
| PATCH | `/<uuid:pk>/assign/` | Bearer | `super_admin`, `admin_area` |
| POST | `/<uuid:pk>/complete/` | Bearer | segun acceso por area/owner/assignee |
| GET | `/<uuid:pk>/attachments/` | Bearer | segun acceso por area/owner/assignee |
| POST | `/<uuid:pk>/attachments/` | Bearer | segun acceso por area/owner/assignee |
| DELETE | `/<uuid:pk>/attachments/<uuid:attachment_pk>/` | Bearer | `super_admin`, `admin_area` de area, uploader |
| GET | `/<uuid:pk>/logs/` | Bearer | segun acceso por area/owner/assignee |

## Estados de actividad

Valores validos de `status`: `inbox`, `today`, `tomorrow`, `scheduled`, `pending`, `completed`.

## Detalle

### `GET /api/activities/`
- Objetivo: listar actividades segun alcance de usuario.
- Alcance:
  - `super_admin`: todas.
  - `admin_area`: actividades de su area.
  - `trabajador`: propias (`owner`) o asignadas (`assigned_to`).
- Response `200`: paginado por configuracion DRF (`count`, `next`, `previous`, `results`).

### `POST /api/activities/`
- Objetivo: crear actividad.
- Request ejemplo:
```json
{
  "title": "Preparar reporte",
  "description": "Q2",
  "status": "inbox",
  "area": "uuid_area",
  "project": "uuid_project",
  "assigned_to": "uuid_user",
  "target_date": "2026-04-10"
}
```
- Regla: `owner` se fuerza al usuario autenticado.
- Response `201`.
- Errores: `400`, `401`, `403`.

### `GET /api/activities/<uuid:pk>/`
- Objetivo: detalle de actividad.
- Response `200`.
- Errores: `404` cuando no tiene acceso (no fuga de existencia).

### `PATCH /api/activities/<uuid:pk>/`
- Objetivo: actualizar parcialmente actividad.
- Response `200`.
- Errores: `400`, `404`.
- Seguridad: guarda `_updated_by` para auditoria en signals.

### `DELETE /api/activities/<uuid:pk>/`
- Objetivo: eliminar actividad.
- Reglas de borrado: `super_admin`, `admin_area` de la misma area, o `owner`.
- Response `204`.
- Errores: `403`, `404`.

### `PATCH /api/activities/<uuid:pk>/move/`
- Objetivo: mover estado de actividad.
- Request:
```json
{
  "status": "pending"
}
```
- Response `200`.
- Errores: `400` estado invalido, `404`.
- Seguridad/auditoria: crea evento `moved` en `ActivityLog`.

### `PATCH /api/activities/<uuid:pk>/assign/`
- Objetivo: asignar o desasignar actividad.
- Request:
```json
{
  "assigned_to": "uuid_user"
}
```
- Permisos: `IsAdminAreaOrAbove`.
- Regla: `admin_area` solo en su area.
- Response `200`.
- Errores: `400`, `403`, `404`.
- Seguridad/auditoria: crea evento `assigned`.

### `POST /api/activities/<uuid:pk>/complete/`
- Objetivo: marcar actividad como completada.
- Response `200`.
- Errores: `400` si ya estaba completada, `404`.
- Seguridad/auditoria: actualiza `completed_at` y crea evento `completed`.

### `GET /api/activities/<uuid:pk>/attachments/`
- Objetivo: listar adjuntos de actividad.
- Response `200`: array de adjuntos (`id`, `file`, `uploaded_by`, `created_at`).

### `POST /api/activities/<uuid:pk>/attachments/`
- Objetivo: subir adjunto.
- Content-Type: `multipart/form-data`.
- Campo requerido: `file`.
- Response `201`.
- Errores: `400`, `404`.

### `DELETE /api/activities/<uuid:pk>/attachments/<uuid:attachment_pk>/`
- Objetivo: eliminar adjunto.
- Reglas: `super_admin`, `admin_area` de la misma area, o quien lo subio.
- Response `204`.
- Errores: `403`, `404`.

### `GET /api/activities/<uuid:pk>/logs/`
- Objetivo: consultar historial/auditoria de actividad.
- Response `200`: lista ordenada desc por `created_at`.

## Errores comunes del modulo
- `400`: validaciones.
- `401`: no autenticado.
- `403`: accion no permitida.
- `404`: recurso inaccesible/no encontrado.
