# Pendientes Backend — HiperApp / Focus

**Base URL producción:** `https://focus-backend-u211p.sevalla.app`  
**Última revisión:** 2026-04-06

El frontend Flutter está conectado al backend real. Este documento lista únicamente
los problemas y pendientes detectados en pruebas con la app en dispositivo físico.

---

## Estado general de endpoints

| Endpoint | Método | Estado |
|---|---|---|
| `GET /api/auth/me/` | GET | ✅ OK |
| `POST /api/auth/login/` | POST | ✅ OK |
| `POST /api/auth/logout/` | POST | ✅ OK |
| `POST /api/auth/refresh/` | POST | ✅ OK |
| `GET /api/activities/` | GET | ✅ OK |
| `POST /api/activities/` | POST | ✅ OK |
| `GET/PATCH/DELETE /api/activities/{uuid}/` | — | ✅ OK |
| `POST /api/activities/{uuid}/move/` | POST | ✅ OK |
| `POST /api/activities/{uuid}/assign/` | POST | ✅ OK |
| `POST /api/activities/{uuid}/complete/` | POST | ✅ OK |
| `GET/POST /api/activities/{uuid}/attachments/` | — | ✅ OK |
| `GET /api/areas/` | GET | ✅ OK |
| `GET /api/users/` | GET | ✅ OK |
| `POST /api/users/invite/` | POST | ✅ OK — falta campo `code` (ver §1) |
| `GET /api/users/invite/verify/` | GET | ❌ Pendiente (ver §2) |
| `POST /api/users/accept-invite/` | POST | ⚠️ Parcial — no acepta `code` (ver §3) |
| `GET /api/projects/` | GET | 🔴 Error 500 (ver §4) |
| `GET /api/stats/personal/` | GET | ❓ Sin probar |
| `GET /api/stats/global/` | GET | ❓ Sin probar |
| `GET /api/stats/workers/` | GET | ❓ Sin probar |
| `GET /api/stats/area/{uuid}/` | GET | ❓ Sin probar |

---

## 🔴 §4 — `GET /api/projects/` devuelve 500

### Síntoma
```
[API] ✗ 500 GET https://focus-backend-u211p.sevalla.app/api/projects/
<!doctype html><html><head><title>Server Error (500)</title></head>...
```
El endpoint responde con una página HTML de Django en lugar de JSON.

### Impacto
- La pantalla **Proyectos** no carga
- El **dropdown de proyectos** en "Capturar actividad" aparece vacío
- Anteriormente también tumbaba el tablero entero (ya corregido en el frontend con `catchError`)

### Solución esperada
El endpoint debe devolver JSON válido. En producción con `DEBUG=False`, Django
suprime los errores detallados — revisar los logs del servidor para ver el traceback real.

---

## ❌ §2 — `GET /api/users/invite/verify/` no existe

### Contrato esperado por el frontend
```
GET /api/users/invite/verify/?code=IZJC5DB3
(sin Authorization header — endpoint público)
```

### Respuesta 200 — código válido:
```json
{
  "role":       "trabajador",
  "area_name":  "Test Area",
  "expires_at": "2026-04-07T18:00:00Z"
}
```

### Respuestas de error 400:
```json
{ "code": "Código inválido" }
{ "code": "Esta invitación ya fue utilizada" }
{ "code": "Esta invitación ha expirado" }
```

### Comportamiento
- **No consume** la invitación. Se puede llamar N veces.
- El frontend lo llama antes de mostrar el formulario de registro.

---

## ⚠️ §3 — `POST /api/users/accept-invite/` no acepta campo `code`

### Qué manda el frontend
```json
{
  "code":       "IZJC5DB3",
  "email":      "nuevo@example.com",
  "first_name": "Ana",
  "last_name":  "García",
  "password":   "MiPassword1!"
}
```

### Solución sugerida
Aceptar tanto `code` como `token` (compatibilidad hacia atrás):
```python
identifier = request.data.get('code') or request.data.get('token')
invitation  = Invitation.objects.get(code=identifier)
```

### Respuesta 201 esperada:
```json
{
  "id":         "uuid",
  "email":      "nuevo@example.com",
  "first_name": "Ana",
  "last_name":  "García",
  "role":       "trabajador",
  "area_id":    "uuid"
}
```

---

## ✅ §1 — `POST /api/users/invite/` — agregar campo `code` en respuesta

El endpoint ya funciona pero devuelve solo `token` (JWT largo, difícil de compartir).

### Agregar `code` a la respuesta:
```json
{
  "code":       "IZJC5DB3",
  "token":      "eyJhbGci...",
  "expires_at": "2026-04-07T18:00:00Z",
  "role":       "trabajador",
  "area_id":    "uuid"
}
```

El `code` debe ser único (8 chars A-Z0-9), válido 24 horas, un solo uso.  
El frontend ya hace `map['code'] ?? map['token']` como fallback mientras no exista.

---

## Flujo de invitación completo (referencia)

```
SA/AA                         Backend                      Invitado (Flutter)
─────                         ───────                      ──────────────────
POST /users/invite/   ──►    genera code + token
{ area, role }        ◄──    { code: "IZJC5DB3", ... }
Copia "IZJC5DB3"
Lo comparte (WhatsApp, etc.)
                                                 Abre app → "Tengo código"
                                                 Escribe: IZJC5DB3
                              GET /users/invite/verify/?code=IZJC5DB3  ──►
                                                 ◄──  { role, area_name }
                                                 Ve: "Trabajador · Test Area ✓"
                                                 Llena: nombre, email, password
                              POST /users/accept-invite/  ──►
                              { code, email, first_name, last_name, password }
                                                 ◄──  { id, email, role }
                                                 → Redirige a Login
```

---

## Credenciales de prueba actuales

| Usuario | Email | Password | Rol |
|---|---|---|---|
| Super Admin | admin@focus.com | Admin123! | super_admin |
| Invitado (ya creado) | nuevo@focus.com | Pass1234! | trabajador |
