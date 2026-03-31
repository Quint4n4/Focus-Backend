# Endpoints — Usuarios

Base URL: `http://localhost:8000/api/users/`

## Resumen

Gestion de usuarios internos e invitaciones de alta.

## Tabla rapida

| Metodo | Ruta | Auth | Roles |
|---|---|---|---|
| GET | `/` | Bearer | `super_admin`, `admin_area` |
| GET | `/<uuid:pk>/` | Bearer | `super_admin`, `admin_area`, `trabajador` (segun alcance) |
| PATCH | `/<uuid:pk>/` | Bearer | `super_admin`, `admin_area`, `trabajador` (restricciones) |
| POST | `/invite/` | Bearer | `super_admin`, `admin_area` |
| POST | `/accept-invite/` | Publico | Todos |

## Detalle por endpoint

### `GET /api/users/`
- Objetivo: listar usuarios visibles para el solicitante.
- Permisos:
  - `super_admin`: ve todos.
  - `admin_area`: solo su area.
- Response `200`: lista de usuarios (`id`, `email`, `first_name`, `last_name`, `role`, `area_id`, `created_at`).
- Errores: `401`, `403`.

### `GET /api/users/<uuid:pk>/`
- Objetivo: consultar detalle de un usuario.
- Reglas de acceso:
  - `super_admin`: cualquiera.
  - `admin_area`: solo usuarios de su area o si mismo.
  - `trabajador`: solo si mismo.
- Response `200`: detalle (`biometrics_enabled`, `onboarding_completed`, `updated_at`, etc).
- Errores: `401`, `404` cuando no debe revelar existencia.

### `PATCH /api/users/<uuid:pk>/`
- Objetivo: actualizacion parcial de usuario.
- Campos editables esperados: `first_name`, `last_name` (otros campos sensibles son readonly en serializer).
- Reglas:
  - `super_admin`: puede editar usuarios.
  - `admin_area`: solo puede editarse a si mismo.
  - `trabajador`: solo puede editarse a si mismo.
- Response `200`: usuario actualizado.
- Errores: `400`, `401`, `403`, `404`.

### `POST /api/users/invite/`
- Objetivo: generar invitacion temporal (24h).
- Request:
```json
{
  "area": "uuid_area",
  "role": "trabajador"
}
```
- Response `201`:
```json
{
  "token": "<token_plano_para_compartir>",
  "expires_at": "2026-04-01T12:00:00Z",
  "role": "trabajador",
  "area_id": "uuid_area"
}
```
- Errores:
  - `403` si `admin_area` intenta invitar fuera de su area.
  - `429` limite alcanzado.
- Seguridad:
  - rate limit `10/h` (`user_or_ip`);
  - en DB solo se guarda hash SHA-256 del token.

### `POST /api/users/accept-invite/`
- Objetivo: registrar un nuevo usuario usando token de invitacion.
- Request:
```json
{
  "token": "<token_plano>",
  "email": "nuevo@focus.com",
  "first_name": "Luis",
  "last_name": "Ramos",
  "password": "Secret123!"
}
```
- Response `201`:
```json
{
  "id": "uuid",
  "email": "nuevo@focus.com",
  "first_name": "Luis",
  "last_name": "Ramos",
  "role": "trabajador"
}
```
- Errores: `400` token invalido/expirado/usado, email invalido, password corta.
- Seguridad: la invitacion se marca `used=true` para evitar reutilizacion.
