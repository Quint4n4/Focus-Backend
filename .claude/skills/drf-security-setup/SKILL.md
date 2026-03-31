---
name: drf-security-setup
description: "ALWAYS use this skill when the user asks to: set up Django REST Framework security, configure a secure Django backend, implement security settings for a DRF API, harden a Django project for production, configure CORS/HTTPS/throttling/headers in Django, or set up protection against brute force, DoS, injection, or data theft in a Django+Flutter backend. Also trigger when user mentions django-axes, django-defender, ScopedRateThrottle, honeypots, UUID PKs, OWASP compliance for Django, or production deployment security for DRF. This skill covers the complete security stack: anti-brute-force, throttling, HTTP headers, secrets management, Docker hardening, logging without sensitive data, and OWASP Top 10 mitigations for Django REST Framework APIs consumed by mobile clients."
---

# DRF Security Setup — Backend seguro profesional 2025

## Contexto del proyecto
Backend Django REST Framework consumido por Flutter. Alineado con OWASP Top 10 2025.

## Orden de implementación

1. Secrets y entorno
2. Dependencias de seguridad
3. Settings de producción
4. Throttling avanzado
5. Protección anti-fuerza-bruta
6. Modelo de datos (UUIDs, serializers)
7. Honeypots
8. Logging seguro
9. Docker e infraestructura

---

## 1. Dependencias

```txt
django>=5.0
djangorestframework>=3.15
djangorestframework-simplejwt>=5.3
django-cors-headers>=4.3
django-axes>=6.4
django-defender>=0.9.7
django-honeypot>=1.0
django-csp>=3.7
python-decouple>=3.8
sentry-sdk[django]>=1.40
```

---

## 2. Gestión de secretos

```python
# settings/base.py
from decouple import config, Csv

SECRET_KEY = config('DJANGO_SECRET_KEY')
JWT_SECRET_KEY = config('JWT_SECRET_KEY')   # SEPARADO del SECRET_KEY
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())
```

```bash
# .env.production (nunca en git)
DJANGO_SECRET_KEY=genera-con-secrets.token_urlsafe-50-chars
JWT_SECRET_KEY=otra-clave-distinta-larga
DEBUG=False
ALLOWED_HOSTS=api.tudominio.com
DATABASE_URL=postgresql://user:pass@db:5432/dbname
REDIS_URL=redis://:password@redis:6379/0
CORS_ALLOWED_ORIGINS=https://tuapp.com
```

> Generar: `python -c "import secrets; print(secrets.token_urlsafe(50))"`

---

## 3. Settings de producción

```python
# settings/production.py
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',  # Sin browsable API
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day',
        'login': '5/min',
        'register': '3/min',
        'password_reset': '3/hour',
        'biometric_setup': '3/hour',
        'token_refresh': '30/min',
    },
}

CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', cast=Csv())
CORS_ALLOW_CREDENTIALS = True
# NUNCA CORS_ALLOW_ALL_ORIGINS = True

CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL'),
    }
}
```

---

## 4. Anti-fuerza bruta (elegir uno)

### django-defender (Redis — recomendado)
```python
INSTALLED_APPS += ['defender']
MIDDLEWARE = ['defender.middleware.FailedLoginMiddleware'] + MIDDLEWARE

DEFENDER_REDIS_URL = config('REDIS_URL')
DEFENDER_LOGIN_FAILURE_LIMIT = 5
DEFENDER_COOLOFF_TIME = 1800
DEFENDER_BEHIND_REVERSE_PROXY = True
DEFENDER_REVERSE_PROXY_HEADER = 'HTTP_X_FORWARDED_FOR'
```

### django-axes (DB — más completo)
```python
INSTALLED_APPS += ['axes']
MIDDLEWARE += ['axes.middleware.AxesMiddleware']
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend',
    'django.contrib.auth.backends.ModelBackend',
]
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=30)
AXES_RESET_ON_SUCCESS = True
```

---

## 5. Honeypots

```python
# urls.py
import logging
from django.core.cache import cache
from django.http import HttpResponse

logger = logging.getLogger('security')

def honeypot_view(request):
    ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
    ip = ip.split(',')[0].strip()
    logger.warning(f"HONEYPOT_HIT ip={ip} path={request.path}")
    cache.set(f'blocked_ip_{ip}', True, timeout=86400)
    return HttpResponse(status=404)

urlpatterns = [
    path('wp-admin/', honeypot_view),
    path('phpmyadmin/', honeypot_view),
    path('api/v0/', honeypot_view),
    path('xmlrpc.php', honeypot_view),
    path('api/v1/', include('api.urls')),
]
```

---

## 6. Modelo seguro — UUIDs + serializers

```python
# models.py
import uuid
from django.db import models

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

# serializers.py — SIEMPRE allowlist, NUNCA exclude ni __all__
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'created_at']
        read_only_fields = ['id', 'created_at', 'is_staff', 'is_admin', 'is_superuser']

    def validate_email(self, value):
        return value.lower().strip()
```

---

## 7. Logging seguro

```python
# security/filters.py
import logging, re

class SensitiveDataFilter(logging.Filter):
    PATTERNS = [
        (re.compile(r'password["\s:=]+\S+', re.I), 'password=[REDACTED]'),
        (re.compile(r'token["\s:=]+\S+', re.I), 'token=[REDACTED]'),
        (re.compile(r'Bearer\s+\S+'), 'Bearer [REDACTED]'),
        (re.compile(r'\b\d{16}\b'), '[CARD_REDACTED]'),
    ]
    def filter(self, record):
        msg = str(record.getMessage())
        for p, r in self.PATTERNS:
            msg = p.sub(r, msg)
        record.msg = msg
        return True

LOGGING = {
    'version': 1,
    'filters': {'sensitive': {'()': 'security.filters.SensitiveDataFilter'}},
    'handlers': {
        'security_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/security.log',
            'maxBytes': 10485760,
            'backupCount': 5,
            'filters': ['sensitive'],
        },
    },
    'loggers': {
        'security': {'handlers': ['security_file'], 'level': 'WARNING'},
    },
}
```

---

## 8. Docker — red privada para DB

Ver `references/docker_infra.md` para el compose completo.

Reglas críticas:
- DB sin puerto expuesto al exterior (sin `ports:` en el servicio db)
- Redis con contraseña obligatoria
- Nginx termina SSL antes de Django
- `.env.production` fuera del repositorio

---

## Checklist pre-deploy

```bash
python manage.py check --deploy
# Verificar manualmente:
# [ ] DEBUG=False
# [ ] SECRET_KEY y JWT_SECRET_KEY no en código
# [ ] CORS sin wildcards
# [ ] Solo JSONRenderer activo
# [ ] HTTPS forzado + HSTS 1 año
# [ ] Throttling por scope en login/register
# [ ] UUID como PKs
# [ ] Serializers con fields allowlist
# [ ] Logs sin tokens ni passwords
# [ ] DB sin puerto público en Docker
```

## Referencias
- `references/docker_infra.md` — Docker Compose completo con Nginx + Postgres + Redis
- `references/brute_force.md` — Comparativa django-axes vs django-defender, configuración avanzada
- `references/owasp-checklist.md` — OWASP Top 10 2025 completo para DRF
