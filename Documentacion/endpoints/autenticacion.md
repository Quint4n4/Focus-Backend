# Endpoints — Autenticacion

Base URL: `http://localhost:8000/api/auth/`

## Resumen

Este modulo gestiona login JWT, logout, refresh, perfil del usuario autenticado y flujo biometrico.

## Tabla rapida

| Metodo | Ruta | Auth | Roles |
|---|---|---|---|
| POST | `/login/` | Publico | Todos |
| POST | `/logout/` | Bearer | `super_admin`, `admin_area`, `trabajador` |
| POST | `/refresh/` | Publico (con refresh) | Todos |
| GET | `/me/` | Bearer | `super_admin`, `admin_area`, `trabajador` |
| POST | `/biometric/enable/` | Bearer | `super_admin`, `admin_area`, `trabajador` |
| POST | `/biometric/disable/` | Bearer | `super_admin`, `admin_area`, `trabajador` |
| POST | `/biometric/login/` | Publico (con refresh + device_id) | Todos |
| POST | `/onboarding/complete/` | Bearer | `super_admin`, `admin_area`, `trabajador` |

## Detalle por endpoint

### `POST /api/auth/login/`
- Objetivo: autenticar por `email`/`password` y emitir par JWT.
- Request:
```json
{
  "email": "user@focus.com",
  "password": "Secret123!"
}
```
- Response `200`:
```json
{
  "access": "<jwt_access>",
  "refresh": "<jwt_refresh>",
  "user": {
    "id": "uuid",
    "email": "user@focus.com",
    "first_name": "Ana",
    "last_name": "Ruiz",
    "role": "trabajador",
    "area_id": "uuid",
    "biometrics_enabled": false,
    "onboarding_completed": false,
    "created_at": "2026-03-31T12:00:00Z"
  }
}
```
- Errores: `401` credenciales invalidas, `429` exceso de intentos.
- Seguridad: rate limit `5/min` por IP y anti brute force con Axes.

### `POST /api/auth/logout/`
- Objetivo: invalidar refresh token (blacklist).
- Request:
```json
{
  "refresh": "<jwt_refresh>"
}
```
- Response `200`:
```json
{
  "detail": "Sesion cerrada correctamente."
}
```
- Errores: `400` si falta/expiro refresh, `401` sin bearer.
- Seguridad: revocacion de sesion por token blacklist.

### `POST /api/auth/refresh/`
- Objetivo: renovar tokens con rotacion.
- Request:
```json
{
  "refresh": "<jwt_refresh>"
}
```
- Response `200` (SimpleJWT):
```json
{
  "access": "<jwt_access_nuevo>",
  "refresh": "<jwt_refresh_nuevo>"
}
```
- Errores: `401` token invalido, `429` exceso de refresh.
- Seguridad: `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True`, rate limit `20/min`.

### `GET /api/auth/me/`
- Objetivo: devolver perfil del usuario autenticado.
- Response `200`: mismo esquema de `user` del login.
- Errores: `401` si no hay bearer valido.

### `POST /api/auth/biometric/enable/`
- Objetivo: activar biometria y registrar `device_id`.
- Request:
```json
{
  "device_id": "device-abc-123"
}
```
- Response `200`:
```json
{
  "detail": "Autenticacion biometrica activada.",
  "biometrics_enabled": true,
  "device_id": "device-abc-123"
}
```
- Errores: `400` si `device_id` vacio, `401` sin bearer.

### `POST /api/auth/biometric/disable/`
- Objetivo: desactivar biometria y limpiar `device_id`.
- Response `200`:
```json
{
  "detail": "Autenticacion biometrica desactivada."
}
```
- Errores: `401` sin bearer.

### `POST /api/auth/biometric/login/`
- Objetivo: login sin password usando refresh previo + `device_id`.
- Request:
```json
{
  "device_id": "device-abc-123",
  "refresh": "<jwt_refresh>"
}
```
- Response `200`: igual que login (`access`, `refresh`, `user`).
- Errores:
  - `400` faltan campos.
  - `401` refresh invalido o usuario inexistente.
  - `403` biometria no activa, `device_id` distinto o cuenta inactiva.
- Seguridad: valida vinculacion del dispositivo y rota refresh al emitir nuevo par.

### `POST /api/auth/onboarding/complete/`
- Objetivo: marcar onboarding como completado.
- Response `200`:
```json
{
  "detail": "Onboarding completado.",
  "user": {
    "id": "uuid"
  }
}
```
- Errores: `401` sin bearer.

## Errores comunes del modulo

- `400`: payload invalido o faltante.
- `401`: token invalido/no autenticado.
- `403`: regla de negocio o estado de cuenta/dispositivo.
- `429`: rate limiting.
