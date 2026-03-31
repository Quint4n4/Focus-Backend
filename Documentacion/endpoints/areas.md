# Endpoints — Areas

Base URL: `http://localhost:8000/api/areas/`

## Tabla rapida

| Metodo | Ruta | Auth | Roles |
|---|---|---|---|
| GET | `/` | Bearer | `super_admin`, `admin_area`, `trabajador` |
| POST | `/` | Bearer | `super_admin` |
| GET | `/<uuid:pk>/` | Bearer | `super_admin`, `admin_area`, `trabajador` |
| PUT/PATCH | `/<uuid:pk>/` | Bearer | `super_admin` |
| DELETE | `/<uuid:pk>/` | Bearer | `super_admin` |
| GET | `/<uuid:pk>/members/` | Bearer | `super_admin`, `admin_area`, `trabajador` (solo su area si no es super) |

## Detalle

### `GET /api/areas/`
- Objetivo: listar areas visibles.
- Reglas:
  - `super_admin`: todas.
  - `admin_area` y `trabajador`: solo su area.
- Response `200`: lista de areas (`id`, `name`, `description`, `created_by`, timestamps).

### `POST /api/areas/`
- Objetivo: crear area.
- Request:
```json
{
  "name": "Operaciones",
  "description": "Equipo de operaciones"
}
```
- Response `201`: area creada con representacion completa.
- Errores: `400`, `401`, `403`.

### `GET /api/areas/<uuid:pk>/`
- Objetivo: obtener detalle de area.
- Response `200`.
- Errores: `401`, `404`.

### `PUT/PATCH /api/areas/<uuid:pk>/`
- Objetivo: actualizar area.
- Solo `super_admin`.
- Response `200`.
- Errores: `400`, `401`, `403`, `404`.

### `DELETE /api/areas/<uuid:pk>/`
- Objetivo: eliminar area.
- Solo `super_admin`.
- Response `204`.
- Errores: `401`, `403`, `404`.

### `GET /api/areas/<uuid:pk>/members/`
- Objetivo: listar miembros de un area.
- Reglas:
  - `super_admin`: cualquier area.
  - `admin_area` y `trabajador`: solo su area.
- Response `200`: lista de usuarios (`id`, `email`, `first_name`, `last_name`, `role`, `created_at`).
- Nota: para no autorizados no-super sobre otra area, la vista retorna conjunto vacio (sin fuga de informacion sensible).
