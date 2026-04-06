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
    import socket
    import traceback
    db_settings = settings.DATABASES.get('default', {})
    host = db_settings.get('HOST', '')
    port = int(db_settings.get('PORT') or 5432)
    info = {
        'host': host,
        'port': port,
        'name': db_settings.get('NAME', 'N/A'),
        'user': db_settings.get('USER', 'N/A'),
        'engine': db_settings.get('ENGINE', 'N/A'),
        'options': db_settings.get('OPTIONS', {}),
    }

    # Test 1: TCP reachability
    try:
        sock = socket.create_connection((host, port), timeout=5)
        sock.close()
        info['tcp_status'] = 'ok'
    except Exception as e:
        info['tcp_status'] = 'error'
        info['tcp_error'] = str(e)

    # Test 2: PostgreSQL connection + active queries
    try:
        from django.db import connection
        connection.close()
        connection.ensure_connection()
        info['db_status'] = 'ok'
        info['status'] = 'ok'

        # Queries activas (útil para detectar deadlocks/queries lentas)
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT pid, state, wait_event_type, wait_event,
                       EXTRACT(EPOCH FROM (now() - query_start))::int AS duration_s,
                       LEFT(query, 120) AS query
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND state != 'idle'
                ORDER BY duration_s DESC NULLS LAST
                LIMIT 10
            """)
            cols = [c.name for c in cursor.description]
            info['active_queries'] = [dict(zip(cols, row)) for row in cursor.fetchall()]
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
