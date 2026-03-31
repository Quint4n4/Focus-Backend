---
name: migrate
description: Crea y aplica migraciones de Django para el proyecto Focus
argument-hint: "[nombre_app]"
---

Gestiona las migraciones de Django para el proyecto Focus.

Si se pasa un argumento ($ARGUMENTS), ejecuta las migraciones solo para esa app.
Si no hay argumentos, ejecuta para todas las apps.

Pasos:
1. Primero revisa el estado actual con `python manage.py showmigrations`
2. Genera las migraciones: `python manage.py makemigrations $ARGUMENTS`
3. Aplica las migraciones: `python manage.py migrate $ARGUMENTS`
4. Verifica que no haya errores
5. Reporta qué migraciones se aplicaron

Usa el entorno virtual si existe (venv\Scripts\activate en Windows).
El DJANGO_SETTINGS_MODULE es config.settings.local.
