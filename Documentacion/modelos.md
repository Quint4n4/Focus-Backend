# Modelos de Datos

Resumen de entidades principales del backend.

## `authentication.User`

- PK: `UUID`.
- Campos clave:
  - `email` (unico, `USERNAME_FIELD`);
  - `first_name`, `last_name`;
  - `role`: `super_admin | admin_area | trabajador`;
  - `area` (FK a `areas.Area`, nullable);
  - `biometrics_enabled`, `device_id`;
  - `onboarding_completed`;
  - `is_active`, `is_staff`.
- Relacion funcional: identidad y autorizacion base del sistema.

## `areas.Area`

- PK: `UUID`.
- Campos: `name`, `description`, `created_by`, `created_at`, `updated_at`.
- Relacion: agrupa usuarios, actividades y proyectos por dominio de negocio.

## `users.Invitation`

- PK: `UUID`.
- Campos: `token_hash`, `area`, `role`, `created_by`, `expires_at`, `used`, `created_at`.
- Seguridad:
  - token plano no se almacena;
  - validacion por hash y expiracion.

## `activities.Activity`

- PK: `UUID`.
- Campos:
  - `title`, `description`, `status`;
  - `owner`, `assigned_to`, `assigned_by`;
  - `area`, `project`;
  - `target_date`, `completed_at`, timestamps.
- Flujo de estados: `inbox -> today/tomorrow/scheduled/pending -> completed`.

## `activities.ActivityLog`

- PK: `UUID`.
- Campos: `activity`, `user`, `event_type`, `detail`, `created_at`.
- Eventos: `created`, `updated`, `moved`, `assigned`, `completed`, `deleted`.
- Uso: trazabilidad y auditoria.

## `activities.ActivityAttachment`

- PK: `UUID`.
- Campos: `activity`, `file`, `uploaded_by`, `created_at`.
- Uso: adjuntos por actividad.

## `projects.Project`

- PK: `UUID`.
- Campos: `name`, `description`, `area`, `created_by`, `status`, `target_date`, timestamps.
- Estado: `active | archived`.

## Relaciones clave

- Un `Area` tiene muchos `User`, `Activity`, `Project`.
- Un `Project` tiene muchas `Activity`.
- Una `Activity` tiene muchos `ActivityLog` y `ActivityAttachment`.
- `Invitation` crea usuarios vinculados a un `Area` y `role` predefinido.
