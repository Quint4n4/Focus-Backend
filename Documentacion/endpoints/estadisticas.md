# Endpoints — Estadisticas

Base URL: `http://localhost:8000/api/stats/`

## Tabla rapida

| Metodo | Ruta | Auth | Roles |
|---|---|---|---|
| GET | `/personal/` | Bearer | `super_admin`, `admin_area`, `trabajador` |
| GET | `/area/<uuid:area_pk>/` | Bearer | `super_admin`, `admin_area` |
| GET | `/drilldown/` | Bearer | `super_admin`, `admin_area` |

## Detalle

### `GET /api/stats/personal/`
- Objetivo: metricas personales del usuario (`owner`).
- Response `200`:
```json
{
  "by_status": {
    "inbox": 1,
    "today": 0,
    "tomorrow": 1,
    "scheduled": 0,
    "pending": 2,
    "completed": 3
  },
  "completed_today": 1,
  "completed_this_week": 2,
  "completed_this_month": 3,
  "total_owned": 7,
  "total_assigned": 5
}
```
- Errores: `401`, `403`.

### `GET /api/stats/area/<uuid:area_pk>/`
- Objetivo: metricas agregadas de un area + desglose por miembro.
- Reglas:
  - `super_admin`: cualquier area.
  - `admin_area`: solo su area (`403` si consulta otra).
- Response `200`: `area_id`, `total_activities`, `completed_activities`, `completion_rate`, `by_status`, `members`.
- Errores: `403`, `404`.

### `GET /api/stats/drilldown/`
- Objetivo: analitica filtrable y agregada.
- Query params opcionales:
  - `area=<uuid>`
  - `project=<uuid>`
  - `user=<uuid>` (owner)
  - `from=YYYY-MM-DD`
  - `to=YYYY-MM-DD`
- Regla:
  - para `admin_area`, el filtro de area se fuerza a su propia area.
- Response `200`:
```json
{
  "filters": {},
  "summary": {
    "total": 10,
    "completed": 4,
    "completion_rate": 40.0
  },
  "by_status": {},
  "by_project": [],
  "by_user": []
}
```
- Errores: `401`, `403`.
