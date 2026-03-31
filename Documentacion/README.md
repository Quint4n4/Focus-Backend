# Focus Backend — Documentación Técnica

Focus es una API REST para gestión de tareas y productividad en equipos. Construida con Django REST Framework, PostgreSQL y Redis.

## Índice

| Documento | Descripción |
|---|---|
| [Arquitectura](arquitectura.md) | Stack tecnológico, estructura del proyecto, decisiones de diseño |
| [Modelos de datos](modelos.md) | Esquema de base de datos, relaciones entre modelos |
| [Endpoints — Autenticación](endpoints/autenticacion.md) | Login, logout, JWT, biométrico, onboarding |
| [Endpoints — Usuarios](endpoints/usuarios.md) | Gestión de usuarios e invitaciones |
| [Endpoints — Áreas](endpoints/areas.md) | CRUD de áreas y gestión de miembros |
| [Endpoints — Actividades](endpoints/actividades.md) | Ciclo de vida de tareas, adjuntos, audit log |
| [Endpoints — Proyectos](endpoints/proyectos.md) | Colecciones de actividades y progreso |
| [Endpoints — Estadísticas](endpoints/estadisticas.md) | Analytics personales, por área y drill-down |
| [Seguridad](seguridad.md) | Autenticación JWT, brute-force, rate limiting, headers, CSP |
| [Despliegue](despliegue.md) | Docker, Nginx, variables de entorno, producción |
| [Plan de tests de endpoints](plan_tests_endpoints.md) | Cobertura funcional, RBAC y seguridad por endpoint |

## Inicio rápido

```bash
# Clonar e instalar dependencias
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements/local.txt

# Configurar entorno
cp .env.example .env
# Editar .env con tus credenciales de PostgreSQL

# Migraciones y servidor
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## URLs base

```
http://localhost:8000/api/auth/
http://localhost:8000/api/users/
http://localhost:8000/api/areas/
http://localhost:8000/api/activities/
http://localhost:8000/api/projects/
http://localhost:8000/api/stats/
```

## Sistema de roles

| Rol | Valor en DB | Capacidades |
|---|---|---|
| Super Administrador | `super_admin` | Acceso total al sistema |
| Administrador de Área | `admin_area` | Gestiona su área y sus miembros |
| Trabajador | `trabajador` | Solo sus propias actividades y datos de área |

## Autenticación

Todos los endpoints (excepto login, accept-invite y biometric/login) requieren el header:

```
Authorization: Bearer <access_token>
```

Los tokens de acceso expiran en **15 minutos**. Usa `POST /api/auth/refresh/` con el refresh token (válido 7 días) para obtener uno nuevo.

## Formato de respuestas de error

Todos los errores tienen el formato estándar:

```json
{
  "error": true,
  "status_code": 400,
  "detail": "Descripción del error"
}
```
