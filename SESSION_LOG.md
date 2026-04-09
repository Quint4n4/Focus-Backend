# Session Log — Test SA → AA → TA + Deploy Prep

**Fecha:** 2026-04-03
**Objetivo:** Probar flujo completo en dispositivo físico: login SA, invitar AA y TA, verificar separación de pantallas.
**Deploy target:** app.sevalla (posterior)

---

## Estado del backend al inicio de sesión

| Check | Estado |
|-------|--------|
| Docker web corriendo | ✅ `0.0.0.0:8000->8000/tcp` |
| Docker redis corriendo | ✅ |
| Todas las migraciones aplicadas | ✅ |
| `authentication.0002_user_personal_role` | ✅ |
| `users.0002_alter_invitation_area_alter_invitation_role` | ✅ |
| `activities.0002_alter_activity_area` | ✅ |

---

## Cambios activos en esta build

1. **Jerarquía invitaciones** — AA solo invita TA; SA puede invitar SA/AA/TA
2. **`Activity.area` nullable** — actividades personales sin área funcionan
3. **`project_id` en ActivityListSerializer** — Flutter puede determinar scope personal/equipo
4. **`Invitation.area` nullable** — invitaciones SA no requieren área

---

## Log de requests / errores

<!-- Ir añadiendo entradas conforme se prueba -->

### [HH:MM] — Descripción
```
REQUEST:  METHOD /endpoint
RESPONSE: status_code
ERROR:    (si aplica)
```

---

## Issues encontrados durante prueba

| # | Endpoint | Síntoma | Estado |
|---|----------|---------|--------|
| 1 | `POST /api/users/invite/` con `role=super_admin` | `KeyError: 'area'` — serializer usaba `['area']` en vez de `.get('area')` | ✅ Corregido |

---

## Notas para deploy en Sevalla

### Variables de entorno requeridas
```env
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY=<generar con secrets.token_urlsafe(50)>
JWT_SECRET_KEY=<generar con secrets.token_urlsafe(50)>
DEBUG=False
DATABASE_URL=postgres://user:pass@host:5432/focus
REDIS_URL=redis://host:6379/0
CORS_ALLOWED_ORIGINS=https://tu-dominio.com
```

### Checklist pre-deploy Sevalla
- [ ] `DEBUG=False` en producción
- [ ] `ALLOWED_HOSTS` con el dominio de Sevalla
- [ ] `CORS_ALLOWED_ORIGINS` con la URL del cliente Flutter
- [ ] `collectstatic` ejecutado
- [ ] Migraciones corridas en la DB de producción
- [ ] Superusuario SA creado en producción
- [ ] `JWT_SECRET_KEY` distinto de `SECRET_KEY`
- [ ] Redis conectado (para JWT blacklist y rate limiting)
