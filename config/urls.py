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

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
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
