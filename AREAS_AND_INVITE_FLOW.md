# Flujo SA: Crear Área + Invitar usuarios

Este documento describe los endpoints y contratos exactos para implementar
`createArea` y el flujo completo de invitación en Flutter.

---

## Endpoints involucrados

| Paso | Método | URL | Rol requerido |
|------|--------|-----|---------------|
| 1 | `GET` | `/api/areas/` | Todos (SA ve todas, AA/TA solo la suya) |
| 2 | `POST` | `/api/areas/` | Solo **SA** |
| 3 | `POST` | `/api/users/invite/` | SA o AA |
| 4 | `POST` | `/api/users/accept-invite/` | Público (sin token JWT) |

---

## Paso 1 — Listar áreas

```
GET /api/areas/
Authorization: Bearer <access_token>
```

**Respuesta 200:**
```json
[
  {
    "id": "ca17493b-fcd9-4dd8-b0ca-a323b3995aa1",
    "name": "Desarrollo",
    "description": "Equipo de dev",
    "created_by": {
      "id": "uuid",
      "email": "admin@focus.com",
      "full_name": "Super Admin"
    },
    "created_at": "2026-04-03T...",
    "updated_at": "2026-04-03T..."
  }
]
```

> SA ve todas las áreas. AA y TA solo ven la suya (lista de 1 elemento).

---

## Paso 2 — Crear área (solo SA)

```
POST /api/areas/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "Marketing",
  "description": "Equipo de marketing"   ← opcional
}
```

**Respuesta 201:** mismo formato que GET individual arriba.

**Errores:**
- `403` si el rol no es `super_admin`
- `400` si `name` está vacío

---

## Paso 3 — Crear invitación

```
POST /api/users/invite/
Authorization: Bearer <access_token>
Content-Type: application/json
```

### SA invitando AA o TA (requiere area):
```json
{
  "area": "ca17493b-fcd9-4dd8-b0ca-a323b3995aa1",
  "role": "admin_area"
}
```
```json
{
  "area": "ca17493b-fcd9-4dd8-b0ca-a323b3995aa1",
  "role": "trabajador"
}
```

### SA invitando otro SA (sin area):
```json
{
  "role": "super_admin"
}
```

### AA invitando TA (solo puede usar su propia area):
```json
{
  "area": "<el area_id del AA>",
  "role": "trabajador"
}
```

**Respuesta 201:**
```json
{
  "token": "AXoPBBK3QXNBeUCQL3Pg...",
  "expires_at": "2026-04-04T18:36:49.123456Z",
  "role": "admin_area",
  "area_id": "ca17493b-fcd9-4dd8-b0ca-a323b3995aa1"
}
```
> `area_id` es `null` para invitaciones de tipo `super_admin`.

**Errors de jerarquía:**
- `403` si AA intenta `role=admin_area` o `role=super_admin`
- `403` si AA usa un `area` distinto al suyo
- `429` si se superan 10 invitaciones/hora

---

## Paso 4 — Aceptar invitación (registro del usuario invitado)

```
POST /api/users/accept-invite/
(sin JWT — endpoint público)
Content-Type: application/json

{
  "token": "AXoPBBK3QXNBeUCQL3Pg...",
  "email": "nuevo@example.com",
  "first_name": "Carlos",
  "last_name": "López",
  "password": "minimo8chars"
}
```

**Respuesta 201:**
```json
{
  "id": "uuid",
  "email": "nuevo@example.com",
  "first_name": "Carlos",
  "last_name": "López",
  "role": "admin_area"
}
```

**Errores:**
- `400 token: Token inválido` — token incorrecto
- `400 token: Esta invitación ya fue utilizada`
- `400 token: Esta invitación ha expirado` — pasaron más de 24h

---

## Flujo completo en Flutter (SA)

```
TeamScreen (SA)
  └── botón "Crear área"
        └── Dialog: {name, description?}
              └── POST /api/areas/
                    └── éxito → actualiza lista de áreas
                          └── botón "Invitar"
                                └── Dialog: {area (dropdown), role (AA/TA/SA)}
                                      └── POST /api/users/invite/
                                            └── éxito → mostrar token/link de invitación
                                                  └── compartir via deep link
                                                        /invite/:token
```

## Flujo completo en Flutter (AA)

```
TeamScreen (AA)
  └── botón "Invitar TA" (area ya es la suya — fija)
        └── Dialog: {solo datos del usuario}
              └── POST /api/users/invite/ {area: user.area_id, role: "trabajador"}
                    └── éxito → mostrar/compartir token
```

---

## Repositorio Flutter a implementar

```dart
// En AreaRepository (nuevo archivo o en UsersRepository)

Future<AreaModel> createArea({
  required String name,
  String? description,
}) async {
  final response = await _dio.post(
    ApiEndpoints.areas,  // '/api/areas/'
    data: {
      'name': name,
      if (description != null) 'description': description,
    },
  );
  return AreaModel.fromJson(response.data);
}
```

```dart
// En UsersRepository (método ya debe existir como generateInvite)

Future<InviteResult> generateInvite({
  String? areaId,          // null solo para role=super_admin
  required String role,    // 'super_admin' | 'admin_area' | 'trabajador'
}) async {
  final response = await _dio.post(
    ApiEndpoints.invite,   // '/api/users/invite/'
    data: {
      if (areaId != null) 'area': areaId,
      'role': role,
    },
  );
  return InviteResult.fromJson(response.data);
}
```

---

## Notas de implementación UI

- **Dropdown de áreas en el diálogo de invitación (SA):** cargar con `GET /api/areas/` al abrir el dialog.
- **AA:** el campo `area` es fijo (`user.area_id`), no mostrar dropdown.
- **El token retornado** se convierte en deep link: `focusapp://invite/<token>` o `https://tu-dominio/invite/<token>`.
- **`accept-invite`** es público → llamarlo sin Dio interceptors de auth.
