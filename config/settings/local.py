from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ['*']

# ── Base de datos — SQLite para dev rápido ──
# Si se define DATABASE_URL en .env se usa PostgreSQL automáticamente.
import dj_database_url  # noqa: E402
from decouple import config  # noqa: E402

_db_url = config('DATABASE_URL', default='')

if _db_url:
    DATABASES = {
        'default': dj_database_url.parse(_db_url, conn_max_age=600)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ── Debug Toolbar ──
INSTALLED_APPS += ['debug_toolbar']  # noqa: F405

MIDDLEWARE += [  # noqa: F405
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

INTERNAL_IPS = ['127.0.0.1']

# ── Email — imprime en consola ──
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ── Cache — fallback a memoria en local si Redis no está disponible ──
from decouple import config as _config  # noqa: E402, F811

_redis_url = _config('REDIS_URL', default='')
if not _redis_url:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# ── Logging — solo consola en desarrollo ──
LOGGING['handlers']['console']['formatter'] = 'simple'  # noqa: F405
LOGGING['handlers']['console']['level'] = 'INFO'  # noqa: F405
for _logger in LOGGING['loggers'].values():  # noqa: F405
    if 'console' not in _logger['handlers']:
        _logger['handlers'].append('console')
    _logger['level'] = 'INFO'

# ── Axes — desactivado en desarrollo para no bloquear durante tests ──
AXES_ENABLED = False
