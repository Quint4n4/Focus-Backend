from .base import *  # noqa: F401, F403
from decouple import config

DEBUG = False

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# ── Base de datos — PostgreSQL ──
import dj_database_url  # noqa: E402

_db = dj_database_url.parse(config('DATABASE_URL'), conn_max_age=600)

# DB_SSLMODE acepta: require | disable | prefer | verify-full
# En Sevalla (Kubernetes interno) probar primero 'require', si falla probar 'disable'
_sslmode = config('DB_SSLMODE', default='require')
_db.setdefault('OPTIONS', {})
_db['OPTIONS']['sslmode'] = _sslmode

DATABASES = {'default': _db}

# ── Seguridad HTTP ──
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS — 1 año, incluir subdominios y preload
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

X_FRAME_OPTIONS = 'DENY'

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# ── Logging — consola en producción (Sevalla captura stdout) ──
LOGGING['loggers']['django']['handlers'] = ['console']  # noqa: F405
LOGGING['loggers']['productivity']['handlers'] = ['console']  # noqa: F405

# ── Content Security Policy (django-csp) ──
MIDDLEWARE = [  # noqa: F405
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'csp.middleware.CSPMiddleware',                           # ← add CSP middleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'axes.middleware.AxesMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CSP_DEFAULT_SRC  = ("'none'",)
CSP_SCRIPT_SRC   = ("'self'",)
CSP_STYLE_SRC    = ("'self'",)
CSP_IMG_SRC      = ("'self'", 'data:')
CSP_FONT_SRC     = ("'self'",)
CSP_CONNECT_SRC  = ("'self'",)
CSP_MEDIA_SRC    = ("'self'",)
CSP_OBJECT_SRC   = ("'none'",)
CSP_FRAME_SRC    = ("'none'",)
CSP_REPORT_URI   = None  # configure if you have a CSP reporting endpoint
