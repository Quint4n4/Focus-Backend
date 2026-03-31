# Endpoints — Proyectos

Base URL: `http://localhost:8000/api/projects/`

## Tabla rapida

| Metodo | Ruta | Auth | Roles |
|---|---|---|---|
| GET | `/` | Bearer | `super_admin`, `admin_area`, `trabajador` |
| POST | `/` | Bearer | `super_admin`, `admin_area` |
| GET | `/<uuid:pk>/` | Bearer | `super_admin`, `admin_area`, `trabajador` (segun area) |
| PATCH | `/<uuid:pk>/` | Bearer | `super_admin`, `admin_area` |
| DELETE | `/<uuid:pk>/` | Bearer | `super_admin`, `admin_area` |
| GET | `/<uuid:pk>/activities/` | Bearer | `super_admin`, `admin_area`, `trabajador` (segun area) |
| GET | `/<uuid:pk>/progress/` | Bearer | `super_admin`, `admin_area`, `trabajador` (segun area) |

## Detalle

### `GET /api/projects/`
- Objetivo: listar proyectos visibles.
- Alcance:
  - `super_admin`: todos.
  - resto: solo proyectos de su area.
- Response `200` paginado (DRF).

### `POST /api/projects/`
- Objetivo: crear proyecto.
- Request:
```json
{
  "name": "Lanzamiento Q3",
  "description": "Roadmap",
  "area": "uuid_area",
  "status": "active",
  "target_date": "2026-06-30"
}
```
- Reglas:
  - `admin_area` solo puede crear en su area.
- Response `201` con serializer de lectura.
- Errores: `400`, `401`, `403`.

### `GET /api/projects/<uuid:pk>/`
- Objetivo: detalle de proyecto.
- Response `200`.
- Errores: `404` fuera de alcance (se usa `NotFound`).

### `PATCH /api/projects/<uuid:pk>/`
- Objetivo: actualizar proyecto.
- Restriccion: `trabajador` recibe `403`.
- Response `200`.
- Errores: `400`, `403`, `404`.

### `DELETE /api/projects/<uuid:pk>/`
- Objetivo: eliminar proyecto.
- Restriccion: `trabajador` recibe `403`.
- Response `204`.
- Errores: `403`, `404`.

### `GET /api/projects/<uuid:pk>/activities/`
- Objetivo: listar actividades del proyecto.
- Response `200` paginado (`page_size=20` en la vista).
- Errores: `404`.

### `GET /api/projects/<uuid:pk>/progress/`
- Objetivo: obtener progreso agregado de actividades.
- Response `200`:
```json
{
  "total": 10,
  "completed": 4,
  "pending": 3,
  "in_progress": 3,
  "completion_percentage": 40.0
}
```
- Errores: `404`.
