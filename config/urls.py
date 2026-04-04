"""
Router principal de Focus.

Rutas base de la API:
    /api/auth/        → apps.authentication.urls
    /api/users/       → apps.users.urls
    /api/areas/       → apps.areas.urls
    /api/activities/  → apps.activities.urls
    /api/projects/    → apps.projects.urls
    /api/stats/       → apps.stats.urls
"""

import json
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def health_check(request):
    import django.db
    db_settings = settings.DATABASES.get('default', {})
    info = {
        'host': db_settings.get('HOST', 'N/A'),
        'port': db_settings.get('PORT', 'N/A'),
        'name': db_settings.get('NAME', 'N/A'),
        'user': db_settings.get('USER', 'N/A'),
        'engine': db_settings.get('ENGINE', 'N/A'),
    }
    try:
        from django.db import connection
        connection.ensure_connection()
        info['db_status'] = 'ok'
        info['status'] = 'ok'
    except Exception as e:
        info['db_status'] = 'error'
        info['db_error'] = str(e)
        info['status'] = 'degraded'
    return JsonResponse(info)


urlpatterns = [
    path('health/', health_check),
    path('admin/', admin.site.urls),
    path('api/auth/',       include('apps.authentication.urls')),
    path('api/users/',      include('apps.users.urls')),
    path('api/areas/',      include('apps.areas.urls')),
    path('api/activities/', include('apps.activities.urls')),
    path('api/projects/',   include('apps.projects.urls')),
    path('api/stats/',      include('apps.stats.urls')),
]

# Servir archivos de media solo en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Debug Toolbar — solo si está instalada
    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
