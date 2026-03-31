# Protección contra Fuerza Bruta — Referencia Completa

## Comparación: django-axes vs django-defender

| Característica | django-axes | django-defender |
|---|---|---|
| Storage | PostgreSQL (DB) | Redis |
| Velocidad | Más lento (queries DB) | Más rápido |
| Dependencias | Solo Django | Redis requerido |
| Integración DRF | Con decorador | Con middleware custom |
| Mantenimiento | Jazzband (activo) | Jazzband (activo) |
| Recomendado cuando | Sin Redis disponible | Proyecto con Redis ya |

## django-axes — Configuración completa

```python
# settings/production.py
from datetime import timedelta

INSTALLED_APPS += ['axes']

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'axes.middleware.AxesMiddleware',  # Posición importante: después de security
    'corsheaders.middleware.CorsMiddleware',
    # ... resto
]

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Configuración core
AXES_FAILURE_LIMIT = 5               # Intentos antes de bloquear
AXES_COOLOFF_TIME = timedelta(minutes=30)  # Duración del bloqueo
AXES_RESET_ON_SUCCESS = True         # Resetear contador al lograr login
AXES_ENABLED = True
AXES_VERBOSE = False                 # Sin logs extra en producción

# Qué trackear
AXES_LOCKOUT_CALLABLE = None         # Usar comportamiento default
AXES_LOCKOUT_TEMPLATE = 'errors/lockout.html'
AXES_USERNAME_FORM_FIELD = 'email'   # Si usas email en lugar de username

# Cache backend para axes (mejor performance)
AXES_CACHE = 'axes'
CACHES = {
    'default': { ... },
    'axes': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}
```

## django-defender — Configuración completa

```bash
pip install django-defender
```

```python
# settings/production.py
INSTALLED_APPS += ['defender']

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'defender.middleware.FailedLoginMiddleware',  # Después de security
    # ...
]

# Configuración defender
DEFENDER_REDIS_URL = config('REDIS_URL')
DEFENDER_LOGIN_FAILURE_LIMIT = 5
DEFENDER_COOLOFF_TIME = 1800             # 30 minutos en segundos
DEFENDER_LOCKOUT_COOLOFF_TIME = 600      # Tiempo entre intentos para tracking
DEFENDER_ATTEMPT_COOLOFF_TIME = 30       # Ventana de tracking de intentos
DEFENDER_STORE_ACCESS_ATTEMPTS = True
DEFENDER_ACCESS_ATTEMPT_EXPIRATION = 24  # Horas hasta que expira el intento
```

## Protección de endpoints DRF específicos con django-axes

```python
# Para APIs REST (no formularios Django normales), axes requiere integración manual
from axes.handlers.proxy import AxesProxyHandler
from axes.helpers import get_client_ip_address, get_client_username

class LoginView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request, *args, **kwargs):
        # Verificar si la IP está bloqueada antes de intentar autenticación
        if AxesProxyHandler.is_already_locked(request, credentials={
            'username': request.data.get('email', ''),
        }):
            return Response(
                {'error': 'Cuenta bloqueada temporalmente. Intenta en 30 minutos.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        response = super().post(request, *args, **kwargs)

        if response.status_code == 401:
            # Registrar el intento fallido
            AxesProxyHandler.user_login_failed(
                sender=self.__class__,
                credentials={'username': request.data.get('email', '')},
                request=request,
            )
        elif response.status_code == 200:
            # Resetear contador en login exitoso
            AxesProxyHandler.user_logged_in(
                sender=self.__class__,
                request=request,
                user=request.user,
            )

        return response
```

## Rate limiting con django-ratelimit (complemento OWASP)

```bash
pip install django-ratelimit
```

```python
# Decorador para vistas específicas
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited

@ratelimit(key='ip', rate='5/m', method='POST', block=True)
def my_view(request):
    pass

# Para class-based views en DRF
from django_ratelimit.core import is_ratelimited

class SensitiveView(APIView):
    def post(self, request):
        limited = is_ratelimited(
            request=request,
            group='sensitive_operation',
            key='user_or_ip',
            rate='10/h',
            increment=True,
        )
        if limited:
            return Response({'error': 'Límite excedido'}, status=429)
        # lógica normal
```

## Middleware de bloqueo por honeypot

```python
# apps/core/middleware.py
from django.core.cache import cache
from django.http import HttpResponse

class HoneypotBlockMiddleware:
    """Bloquea IPs que hayan tocado endpoints honeypot."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = self._get_ip(request)
        if cache.get(f'honeypot_blocked_{ip}'):
            return HttpResponse(status=403)
        return self.get_response(request)

    def _get_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')
```
