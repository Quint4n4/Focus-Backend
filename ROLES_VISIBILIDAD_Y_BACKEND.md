# Roles, visibilidad en la app y conexión al backend

Este documento describe **qué está implementado hoy** en el cliente Flutter respecto a **SA / AA / TA / cuenta personal**, **dónde vive la lógica**, **qué debe enviar el backend** y **qué queda por endurecer del lado servidor**.

---

## 1. Resumen ejecutivo

| Rol en app (`UserRole`) | Significado de negocio |
|-------------------------|-------------------------|
| `superAdmin` | Super Admin (SA) |
| `adminArea` | Admin de área (AA) |
| `trabajador` | Trabajador de área (TA) |
| `personal` | Usuario solo personal (sin organización; equivalente a “sin rol jerárquico”) |

La separación **sí está hecha en UI y en funciones puras** (`activity_scope.dart`, `projects_access.dart`, `project_kind.dart`). El **repositorio sigue devolviendo listas completas** (salvo parámetros opcionales reservados); el filtrado por rol se aplica **en providers y pantallas** después de combinar usuario + proyectos + actividades.

**Importante:** Historial y detalle de actividad usan en muchos flujos `allActivitiesProvider` **sin** filtrar por rol; al conectar backend conviene definir si esas rutas también deben filtrarse o si el servidor ya no devuelve filas “ajenas”.

---

## 2. Reglas de datos en el cliente (inferencia “tipo B”)

Hasta que el API exponga `scope` o `kind` explícitos, el cliente infiere así:

### 2.1 Proyecto

| Concepto | Regla actual |
|----------|----------------|
| **Proyecto de equipo** | `areaId` no nulo y no vacío (`isTeamProject`) |
| **Proyecto personal** | Sin `areaId` (`isPersonalProject`) |
| **Propietario lógico del proyecto personal** | `ProjectModel.createdById == usuario.id` (`personalProjectsOwnedBy`) |

Archivo: [`lib/core/utils/project_kind.dart`](../lib/core/utils/project_kind.dart).

**Backend:** conviene devolver `area` (o null), `created_by` (id del creador) y, a futuro, `kind: personal | team` para no depender solo de heurísticas.

### 2.2 Actividad (tablero y productividad)

| Concepto | Regla actual |
|----------|----------------|
| **Actividad personal del usuario** | `ownerId == user.id` y (sin proyecto **o** proyecto personal según mapa de proyectos) |
| **Actividad de equipo (AA/TA)** | Usuario con `areaId`: en proyecto de equipo de **su** área, **o** sin proyecto pero `areaId` de la actividad = su área y `ownerId != user.id` (tareas “huérfanas” de otros en el área) |

Archivo: [`lib/core/utils/activity_scope.dart`](../lib/core/utils/activity_scope.dart).

**Backend:** campos útiles: `owner`, `project`, `area`, `assigned_to`; opcional `scope` o `is_team_context` para alinear con el producto sin ambigüedad.

---

## 3. Qué ve cada rol por pantalla (implementado)

### 3.1 Tablero (`DashboardScreen` + `dashboardProvider`)

| Rol | Comportamiento |
|-----|----------------|
| **SA** | Solo actividades **personales** propias (no selector Todas/Personales/Equipo). |
| **Cuenta `personal`** | Igual que SA: solo personales propias. |
| **AA** | Personales + equipo; **SegmentedButton**: Todas / Personales / Equipo (`dashboardScopeUiProvider`). |
| **TA** | Igual que AA (mismo selector). |

Archivos: [`lib/features/dashboard/providers/dashboard_provider.dart`](../lib/features/dashboard/providers/dashboard_provider.dart), [`lib/features/dashboard/screens/dashboard_screen.dart`](../lib/features/dashboard/screens/dashboard_screen.dart).

**Nota:** Si un TA tiene actividades en proyecto de equipo de su área pero no cumple las reglas anteriores, **no** aparecerán en “Equipo” hasta ajustar reglas o el API.

---

### 3.2 Productividad (`StatsScreen`)

| Rol | Comportamiento |
|-----|----------------|
| **SA** | Sección de **actividades personales** (mismo criterio que tablero). **Sin** resumen global ni bloque duplicado “por área”. **Rendimiento por equipos**: lista de AA con % y detalle al tocar (`_AreaDetailSheet`). Lista ordenada por mejor avance medio en proyectos del área en el provider de equipo SA. |
| **AA** | **Personales** + **equipo** (métricas con `personalActivitiesForStats` / `teamActivitiesForStats`). **Rendimiento por equipos**: filas por trabajador vía `workerStatsProvider` (datos mock/API agregados, no recalculados solo con actividades filtradas por proyecto SA→AA). |
| **TA** | **Personales** + **equipo** (dos bloques). Sin lista de “subordinados”. |
| **Cuenta `personal`** | Misma pantalla que TA pero **solo personales** (sin bloque equipo, sin botón de notificaciones de ejemplo org). |

Archivo principal: [`lib/features/stats/screens/stats_screen.dart`](../lib/features/stats/screens/stats_screen.dart).

**Gap backend:** `getWorkerStats` / agregados por TA deberían alinearse con la definición de “actividades en proyectos que el SA asignó al AA”.

---

### 3.3 Proyectos (`ProjectsScreen`)

Pestañas:

| Rol | Pestaña “Personales” | Pestaña “Equipo” / “Para AA” |
|-----|----------------------|------------------------------|
| **SA** | `personalProjectsOwnedBy` | **Para AA**: todos los `isTeamProject` (`saProjectsForAreaAdmins`) |
| **AA / TA** | Personales propios | Proyectos de equipo del `areaId` del usuario |
| **Cuenta `personal`** | Solo personales; **sin** segunda pestaña |

Tarjetas:

- **SA en pestaña “Para AA”**: tarjeta **compacta** (nombre, descripción, AA/área, estado, barra de avance).
- **Resto de casos relevantes**: tarjeta **detallada** (actividades por estado, barra; en proyectos de equipo para AA/TA se puede mostrar asignación en listado corto).

Crear proyecto:

| Rol | Comportamiento |
|-----|----------------|
| **SA** | Diálogo: **Personal** (sin `areaId`) o **Para administrador de área** (dropdown de áreas desde `allAreasStatsProvider`). |
| **AA / TA / personal** | Solo creación **sin área** (proyecto personal); el mock asigna `createdById` al usuario de sesión. |

Archivo: [`lib/features/projects/screens/projects_screen.dart`](../lib/features/projects/screens/projects_screen.dart).  
Helper reutilizable (parcialmente duplicado en pantalla): [`lib/core/utils/projects_access.dart`](../lib/core/utils/projects_access.dart) (`projectsMainListForUser` existe pero la pantalla usa su propia `_projectsForTab` con la misma intención).

---

### 3.4 Captura (`CaptureScreen`)

Proyectos opcionales en el dropdown: **`projectsForCapture(user, projects)`**

| Rol | Proyectos elegibles |
|-----|---------------------|
| **SA** | Solo personales propios (`createdById`) |
| **AA** | Personales propios + proyectos de equipo de su área |
| **TA** | Solo personales propios |
| **Cuenta `personal`** | Solo personales propios |

Archivo: [`lib/features/capture/screens/capture_screen.dart`](../lib/features/capture/screens/capture_screen.dart).

---

### 3.5 Equipo (`TeamScreen`)

| Rol | Comportamiento |
|-----|----------------|
| **SA** | Tarjetas expandibles por AA: proyectos del área, TA, avance por proyecto. Lista **ordenada** por mejor promedio de avance en proyectos. Texto introductorio de comparativa. |
| **AA** | Lista de **solo TA** del mismo `areaId` (excluye al AA). Botón **invitar TA** (`generateInvite` mock). Tarjetas con métricas/actividades por asignación (`teamScreenDataProvider`). |
| **TA** | Solo **líder AA** y **compañeros TA** del área (excluye a sí mismo). Sin botón de alta. |
| **Cuenta `personal`** | Pantalla CTA: unirse / demo de invitación / info SA (sin listado de equipo). |

Archivos: [`lib/features/team/screens/team_screen.dart`](../lib/features/team/screens/team_screen.dart), [`lib/features/team/providers/team_provider.dart`](../lib/features/team/providers/team_provider.dart).

---

## 4. Modelos y JSON relevantes

### 4.1 Usuario (`UserModel`)

- `role`: string parseado con `UserRole.fromString` ([`lib/shared/enums/user_role.dart`](../lib/shared/enums/user_role.dart)).
- `area_id` / `area_name`: necesarios para AA/TA.
- Helpers: `isSuperAdmin`, `isAdminArea`, `isTrabajador`, `isPersonalAccount`, `isOrgUser` ([`lib/shared/models/user.dart`](../lib/shared/models/user.dart)).

**API sugerida:** devolver siempre `role` explícito; para cuenta solo personal usar `personal` (o el alias acordado).

### 4.2 Proyecto (`ProjectModel`)

- `area` → `areaId`; si es null → personal a nivel de “sin área”.
- `created_by` → `createdById` (obligatorio para que “mis proyectos personales” funcionen con la regla actual).

### 4.3 Actividad (`ActivityModel`)

- `owner`, `project`, `area`, `assigned_to`, etc., como ya mapea `fromJson`.

---

## 5. Repositorios y parámetros reservados

- **Actividades:** [`ActivityRepository.getActivities`](../lib/features/dashboard/data/activity_repository.dart) acepta `scope` opcional; se envía como query `scope` si no es null. **El mock no filtra por `scope` todavía**; el cliente filtra en memoria vía `activity_scope.dart`.
- **Proyectos:** sin filtro por rol en el repositorio; la lista completa se filtra en UI.

**Próximo paso backend:** implementar en servidor los mismos criterios (o devolver solo lo visible) y, cuando sea estable, **reducir o eliminar** el filtrado en cliente para evitar doble fuente de verdad.

---

## 6. Cómo probar roles con mocks

- Variable de entorno **`MOCK_ACT_AS`** en `app.env`: valores como `sa`, `aa`, `ta`, `personal` / `solo` / `usuario` (ver [`lib/core/mock/mock_repositories.dart`](../lib/core/mock/mock_repositories.dart)).
- **Email en login mock:** por ejemplo `superadmin@…`, `personal@…` fuerzan usuario según reglas del mock.
- Usuario de sesión efectivo para crear entidades: **`MockAuthRepository.effectiveSessionUser`**.

Datos de ejemplo: [`lib/core/mock/mock_data.dart`](../lib/core/mock/mock_data.dart) (proyectos personales del SA, del AA, de TA Ana, cuenta Mia, actividades asociadas).

---

## 7. Checklist para conectar backend sin sorpresas

1. **GET /me** (o equivalente): `role`, `area_id`, `area_name`, flags de onboarding.
2. **GET /projects**: incluir `area` (nullable) y **`created_by`** en personales.
3. **GET /activities**: decidir si la lista ya viene **filtrada por rol** o el cliente sigue filtrando; si es global, mantener coherencia con `project` y `area` en cada ítem.
4. **POST /projects**: aceptar `area` opcional; si null → personal; persistir `created_by`.
5. **Stats por trabajador / por área:** alinear contrato con lo que muestra `_AdminAreaStats` y `_SuperAdminStats`.
6. **Historial / detalle:** revisar si deben respetar la misma política de visibilidad que el tablero.
7. **Invitaciones:** endpoint real para `generateInvite` y deep link `/invite/:token` ya previsto en el router.

---

## 8. Brechas conocidas respecto al documento de producto

- **Rendimiento por equipos (AA):** las filas de TA pueden seguir viniendo de **stats agregados mock** y no solo de actividades filtradas “proyectos asignados por SA”.
- **TA en tablero “Equipo”:** solo entran actividades que cumplen `isTeamActivityForUser`; casos límite (p. ej. solo asignadas sin `area` coherente) pueden requerir ajuste de reglas o campos API.
- **`projectsMainListForUser`:** helper definido pero la pantalla de proyectos implementa `_projectsForTab`; si se unifica, evitar divergencias futuras.
- **Seguridad:** todo el filtrado en cliente es **UX**; el backend debe **autorizar** cada recurso.

---

## 9. Índice rápido de archivos

| Tema | Archivo |
|------|---------|
| Roles y labels | `lib/shared/enums/user_role.dart` |
| Usuario | `lib/shared/models/user.dart` |
| Proyecto + `createdById` | `lib/shared/models/project.dart` |
| Actividad | `lib/shared/models/activity.dart` |
| Reglas actividad tablero/stats | `lib/core/utils/activity_scope.dart` |
| Reglas proyecto / captura / listas | `lib/core/utils/projects_access.dart` |
| Tipo proyecto | `lib/core/utils/project_kind.dart` |
| Tablero | `lib/features/dashboard/providers/dashboard_provider.dart`, `.../dashboard_screen.dart` |
| Productividad | `lib/features/stats/screens/stats_screen.dart` |
| Proyectos | `lib/features/projects/screens/projects_screen.dart` |
| Captura | `lib/features/capture/screens/capture_screen.dart` |
| Equipo | `lib/features/team/screens/team_screen.dart`, `.../team_provider.dart` |
| Mocks sesión | `lib/core/mock/mock_repositories.dart`, `lib/core/mock/mock_data.dart` |

---

*Última actualización alineada con la implementación en el repositorio (cliente Flutter). Actualizar este archivo cuando cambien reglas de negocio o contratos de API.*
