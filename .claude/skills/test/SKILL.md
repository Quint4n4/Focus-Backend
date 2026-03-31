---
name: test
description: Ejecuta los tests del proyecto Focus. Acepta nombre de app o test específico como argumento.
argument-hint: "[app_o_test_path]"
---

Ejecuta los tests del proyecto Focus Django.

Si se pasa un argumento ($ARGUMENTS), ejecuta solo esos tests.
Si no hay argumentos, ejecuta todos los tests.

Ejemplos de uso:
- /test → todos los tests
- /test apps.authentication → tests de authentication
- /test apps.authentication.tests.test_views.LoginViewTest → test específico

Pasos:
1. Verifica que el entorno virtual esté activo
2. Ejecuta: `python manage.py test $ARGUMENTS --verbosity=2`
3. Muestra un resumen de resultados: tests pasados, fallidos, errores
4. Si hay fallos, muestra el traceback completo y sugiere cómo corregirlo

El DJANGO_SETTINGS_MODULE es config.settings.local.
