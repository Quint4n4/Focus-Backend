# Seguridad del Backend

Este documento describe controles de seguridad implementados en el proyecto y riesgos residuales actuales.

## 1) Autenticacion y sesion

- JWT con `djangorestframework-simplejwt`.
- Access token: 15 minutos.
- Refresh token: 7 dias.
- Rotacion activa: cada refresh invalida el anterior (`BLACKLIST_AFTER_ROTATION=True`).
- Logout invalida refresh via blacklist.
- Header requerido: `Authorization: Bearer <access_token>`.

## 2) Proteccion anti brute-force y abuso

- Django Axes activo:
  - limite: 5 intentos fallidos;
  - enfriamiento: 30 minutos;
  - criterio de bloqueo: `username + ip_address`.
- Rate limit por endpoint (`django-ratelimit`):
  - login: `5/min` por IP;
  - refresh: `20/min` por IP;
  - invite: `10/h` por usuario/IP.
- Rate limit perimetral en Nginx:
  - `/api/auth/login/`: `5r/m`;
  - `/api/users/invite/`: `10r/h`;
  - `/api/*`: `60r/m`.

## 3) Autorizacion (RBAC + alcance)

Permisos de `core.permissions`:
- `IsSuperAdmin`
- `IsAdminAreaOrAbove`
- `IsWorkerOrAbove`

Controles adicionales en vistas:
- aislamiento por area para `admin_area`;
- acceso por ownership/assignment para `trabajador`;
- uso de `NotFound` en varios flujos para no filtrar existencia de recursos.

## 4) Seguridad HTTP en produccion

Configurado en `config/settings/production.py` y `nginx/nginx.conf`:
- redireccion HTTP -> HTTPS;
- HSTS (1 anio, subdominios, preload);
- `X-Frame-Options: DENY`;
- `X-Content-Type-Options: nosniff`;
- CSP con `django-csp` (`default-src 'none'`, origen propio para recursos permitidos);
- cookies de sesion/CSRF con banderas `Secure`, `HttpOnly`, `SameSite=Lax`.

## 5) CORS, secretos y configuracion

- `CORS_ALLOWED_ORIGINS` desde variables de entorno.
- `CORS_ALLOW_CREDENTIALS=True`.
- Secretos en entorno: `SECRET_KEY`, `JWT_SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`.
- Clave JWT separada de `SECRET_KEY` (con fallback si no se define).

## 6) Integridad y trazabilidad

- IDs UUID en modelos principales para reducir enumeracion de recursos.
- Invitaciones con token hasheado SHA-256 (no se guarda token plano).
- Auditoria de actividades:
  - signals para `created`, `updated`, `deleted`;
  - eventos explicitos `moved`, `assigned`, `completed`.
- Logging rotativo:
  - `django.log`;
  - `security.log`;
  - `errors.log`.

## 7) Cobertura por amenaza (resumen)

| Amenaza | Mitigacion implementada |
|---|---|
| Fuerza bruta de login | Axes + ratelimit + limite en Nginx |
| Robo/reuso de refresh token | Rotacion + blacklist + logout con revocacion |
| Enumeracion de IDs | UUID como PK |
| Acceso horizontal entre areas | RBAC + filtros por area/owner/assignee |
| XSS/carga de recursos externos | CSP estricta |
| Clickjacking | `X-Frame-Options: DENY` |
| MITM/downgrade HTTP | HTTPS obligatorio + HSTS |
| Abuso de endpoints | Rate limiting app + edge |

## 8) Riesgos residuales y mejoras recomendadas

1. `JWT_SECRET_KEY` usa fallback a `SECRET_KEY` si falta variable dedicada.  
   Recomendacion: hacerlo obligatorio en produccion para separacion estricta de secretos.
2. Contenedor `web` corre sin usuario no-root definido en `Dockerfile`.  
   Recomendacion: agregar `USER` no privilegiado.
3. Redis en produccion no muestra autenticacion explicita.  
   Recomendacion: exigir password/TLS segun entorno.
4. No hay `DEFAULT_THROTTLE_CLASSES` de DRF (el control actual depende de ratelimit + Nginx).  
   Recomendacion: agregar throttling DRF para cobertura uniforme.

## 9) Checklist rapido pre-release

- [ ] `DEBUG=False`
- [ ] `ALLOWED_HOSTS` y `CORS_ALLOWED_ORIGINS` ajustados a dominios reales
- [ ] `JWT_SECRET_KEY` unico y rotado
- [ ] Certificados TLS validos montados en Nginx
- [ ] Axes y rate limits activos
- [ ] Logs persistidos y monitoreados
- [ ] Pruebas de `401/403/404/429` ejecutadas en endpoints criticos
