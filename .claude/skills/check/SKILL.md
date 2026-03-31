---
name: check
description: Verifica la salud del proyecto Focus: Django system check + migraciones pendientes + tests
---

Realiza una verificación completa del proyecto Focus.

Ejecuta en orden:
1. `python manage.py check` — verifica configuración de Django
2. `python manage.py showmigrations` — muestra estado de migraciones
3. `python manage.py test --verbosity=1` — ejecuta todos los tests

Reporta:
- ✓ si todo está bien
- ✗ con descripción del problema si algo falla
- Lista de migraciones pendientes si las hay

DJANGO_SETTINGS_MODULE=config.settings.local
