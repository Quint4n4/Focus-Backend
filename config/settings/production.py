from .base import *  # noqa: F401, F403
from decouple import config

DEBUG = False

# ── Sentry — error tracking ──
_sentry_dsn = config('SENTRY_DSN', default='')
if _sentry_dsn:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=_sentry_dsn,
            traces_sample_rate=0.1,
            send_default_pii=False,
        )
    except ImportError:
        pass

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# ── Base de datos — PostgreSQL ──
import dj_database_url  # noqa: E402

_db = dj_database_url.parse(config('DATABASE_URL'), conn_max_age=600)

# DB_SSLMODE acepta: require | disable | prefer | verify-full
_sslmode = config('DB_SSLMODE', default='disable')
_db.setdefault('OPTIONS', {})
_db['OPTIONS']['sslmode'] = _sslmode
_db['OPTIONS']['connect_timeout'] = 10
# Mata queries que tarden más de 30s — previene bloqueos en tabla
_db['OPTIONS']['options'] = '-c statement_timeout=30000'

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
    'whitenoise.middleware.WhiteNoiseMiddleware',             # ← sirve /static/ sin Nginx
    'corsheaders.middleware.CorsMiddleware',
    'csp.middleware.CSPMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'axes.middleware.AxesMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# WhiteNoise: comprime y cachea archivos estáticos con hash en el nombre
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# CSP — Django admin requiere 'unsafe-inline' en scripts y estilos
CSP_DEFAULT_SRC  = ("'none'",)
CSP_SCRIPT_SRC   = ("'self'", "'unsafe-inline'")   # admin usa inline scripts
CSP_STYLE_SRC    = ("'self'", "'unsafe-inline'")   # admin usa inline styles
CSP_IMG_SRC      = ("'self'", 'data:')
CSP_FONT_SRC     = ("'self'",)
CSP_CONNECT_SRC  = ("'self'",)
CSP_MEDIA_SRC    = ("'self'",)
CSP_OBJECT_SRC   = ("'none'",)
CSP_FRAME_SRC    = ("'none'",)
CSP_REPORT_URI   = None
