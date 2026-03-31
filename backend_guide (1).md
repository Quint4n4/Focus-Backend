# Productivity App — Guía de Implementación Backend

> **Stack:** Django REST Framework · JWT · PostgreSQL · Docker · Nginx · Gunicorn  
> **Versión:** 1.0 · Tree Tech Solutions · 2026

---

## Índice

1. [Setup inicial del proyecto](#1-setup-inicial-del-proyecto)
2. [Configuración de settings](#2-configuración-de-settings)
3. [Modelo de usuario y autenticación](#3-modelo-de-usuario-y-autenticación)
4. [JWT y permisos personalizados](#4-jwt-y-permisos-personalizados)
5. [App: areas](#5-app-areas)
6. [App: users](#6-app-users)
7. [App: activities](#7-app-activities)
8. [App: projects](#8-app-projects)
9. [App: stats](#9-app-stats)
10. [Logging](#10-logging)
11. [Rate limiting](#11-rate-limiting)
12. [Docker y docker-compose](#12-docker-y-docker-compose)
13. [Nginx y Gunicorn](#13-nginx-y-gunicorn)
14. [Variables de entorno](#14-variables-de-entorno)
15. [Router principal](#15-router-principal)
16. [Checklist de despliegue](#16-checklist-de-despliegue)

---

## 1. Setup inicial del proyecto

### 1.1 Entorno virtual e instalación

```bash
# Crear carpeta del proyecto
mkdir productivity_backend && cd productivity_backend

# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate        # Linux / Mac
venv\Scripts\activate           # Windows

# Instalar dependencias base
pip install django djangorestframework
pip install djangorestframework-simplejwt
pip install django-ratelimit
pip install django-cors-headers
pip install psycopg2-binary      # driver PostgreSQL
pip install python-decouple      # manejo de .env
pip install gunicorn             # servidor WSGI para producción
pip install Pillow               # manejo de imágenes en adjuntos
```

### 1.2 Crear el proyecto Django

```bash
# Crear proyecto con config/ como núcleo
django-admin startproject config .

# Crear directorio de apps
mkdir apps core logs media

# Crear cada app dentro de apps/
python manage.py startapp authentication apps/authentication
python manage.py startapp users apps/users
python manage.py startapp areas apps/areas
python manage.py startapp activities apps/activities
python manage.py startapp projects apps/projects
python manage.py startapp stats apps/stats
```

### 1.3 Estructura final esperada

```
productivity_backend/
├── config/
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── local.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── authentication/
│   ├── users/
│   ├── areas/
│   ├── activities/
│   ├── projects/
│   └── stats/
├── core/
│   ├── permissions.py
│   ├── pagination.py
│   └── exceptions.py
├── logs/
├── media/
├── .env
├── .env.example
├── requirements/
│   ├── base.txt
│   ├── local.txt
│   └── production.txt
├── Dockerfile
├── docker-compose.yml
└── manage.py
```

### 1.4 Requirements

**`requirements/base.txt`**
```
django>=4.2
djangorestframework>=3.14
djangorestframework-simplejwt>=5.3
django-cors-headers>=4.3
django-ratelimit>=4.1
psycopg2-binary>=2.9
python-decouple>=3.8
Pillow>=10.0
gunicorn>=21.0
```

**`requirements/local.txt`**
```
-r base.txt
django-debug-toolbar>=4.2
```

**`requirements/production.txt`**
```
-r base.txt
```

---

## 2. Configuración de settings

### 2.1 `config/settings/base.py`

```python
from pathlib import Path
from decouple import config
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    # Apps del proyecto
    'apps.authentication',
    'apps.users',
    'apps.areas',
    'apps.activities',
    'apps.projects',
    'apps.stats',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
AUTH_USER_MODEL = 'authentication.User'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── REST Framework ──
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.StandardPagination',
    'PAGE_SIZE': 50,
}

# ── JWT ──
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=config('JWT_ACCESS_TOKEN_LIFETIME', default=60, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=config('JWT_REFRESH_TOKEN_LIFETIME', default=7, cast=int)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ── CORS ──
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000').split(',')
```

### 2.2 `config/settings/local.py`

```python
from .base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### 2.3 `config/settings/production.py`

```python
from .base import *
from decouple import config

DEBUG = False
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='db'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Seguridad en producción
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

---

## 3. Modelo de usuario y autenticación

> **Crítico:** El modelo de usuario personalizado debe definirse **antes** de la primera migración. Si ya corriste `migrate`, necesitas resetear la base de datos.

### 3.1 `apps/authentication/models.py`

```python
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super Admin'
        ADMIN_AREA  = 'admin_area',  'Admin de Área'
        TRABAJADOR  = 'trabajador',  'Trabajador de Área'

    # Sobreescribimos username para usar email como login
    username = None
    email = models.EmailField(unique=True)

    role    = models.CharField(max_length=20, choices=Role.choices, default=Role.TRABAJADOR)
    area    = models.ForeignKey(
        'areas.Area',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='members'
    )

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

    @property
    def is_admin_area(self):
        return self.role == self.Role.ADMIN_AREA

    @property
    def is_trabajador(self):
        return self.role == self.Role.TRABAJADOR

    def __str__(self):
        return f'{self.full_name} <{self.email}>'
```

### 3.2 `apps/authentication/serializers.py`

```python
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    area_name = serializers.CharField(source='area.name', read_only=True)

    class Meta:
        model  = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name',
                  'role', 'area', 'area_name', 'date_joined']
        read_only_fields = ['id', 'email', 'role', 'area', 'date_joined']


class UpdateProfileSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'password']

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
```

### 3.3 `apps/authentication/views.py`

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserProfileSerializer, UpdateProfileSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UpdateProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserProfileSerializer(request.user).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            token = RefreshToken(request.data['refresh'])
            token.blacklist()
            return Response({'detail': 'Sesión cerrada correctamente.'})
        except Exception:
            return Response({'detail': 'Token inválido.'}, status=400)
```

### 3.4 `apps/authentication/urls.py`

```python
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import MeView, LogoutView

urlpatterns = [
    path('login/',   TokenObtainPairView.as_view(), name='auth-login'),
    path('refresh/', TokenRefreshView.as_view(),    name='auth-refresh'),
    path('logout/',  LogoutView.as_view(),           name='auth-logout'),
    path('me/',      MeView.as_view(),               name='auth-me'),
]
```

### 3.5 Primera migración

```bash
# Activar settings de local
export DJANGO_SETTINGS_MODULE=config.settings.local

python manage.py makemigrations authentication
python manage.py makemigrations areas
python manage.py makemigrations activities
python manage.py makemigrations projects
python manage.py migrate

# Crear Super Admin inicial
python manage.py createsuperuser
```

---

## 4. JWT y permisos personalizados

### 4.1 `core/permissions.py`

```python
from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """Solo el Super Admin puede acceder."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_super_admin


class IsAdminAreaOrAbove(BasePermission):
    """Admin de Área o Super Admin."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_super_admin or request.user.is_admin_area
        )


class IsOwnerOrAssignee(BasePermission):
    """
    Permite acceso si el usuario es dueño de la actividad,
    está asignado a ella, o tiene rol de admin/SA.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_super_admin or request.user.is_admin_area:
            return True
        return (
            obj.owner_id == request.user.id or
            obj.assigned_to_id == request.user.id
        )


class IsAreaMember(BasePermission):
    """
    El Admin de Área solo puede operar sobre usuarios de su área.
    El Super Admin puede operar sobre cualquier área.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_super_admin:
            return True
        if request.user.is_admin_area:
            return obj.area_id == request.user.area_id
        return False
```

### 4.2 `core/pagination.py`

```python
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200
```

### 4.3 `core/exceptions.py`

```python
from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            'error': True,
            'status_code': response.status_code,
            'detail': response.data,
        }

    return response
```

Registrar el handler en `config/settings/base.py`:

```python
REST_FRAMEWORK = {
    ...
    'EXCEPTION_HANDLER': 'core.exceptions.custom_exception_handler',
}
```

---

## 5. App: areas

### 5.1 `apps/areas/models.py`

```python
from django.db import models
from django.conf import settings


class Area(models.Model):
    name       = models.CharField(max_length=100)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_areas'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'areas'
        ordering = ['name']

    def __str__(self):
        return self.name
```

### 5.2 `apps/areas/serializers.py`

```python
from rest_framework import serializers
from .models import Area


class AreaSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()

    class Meta:
        model  = Area
        fields = ['id', 'name', 'member_count', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_member_count(self, obj):
        return obj.members.count()
```

### 5.3 `apps/areas/views.py`

```python
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from core.permissions import IsSuperAdmin
from .models import Area
from .serializers import AreaSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


class AreaListCreateView(generics.ListCreateAPIView):
    serializer_class   = AreaSerializer
    permission_classes = [IsSuperAdmin]
    queryset           = Area.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AreaDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = AreaSerializer
    permission_classes = [IsSuperAdmin]
    queryset           = Area.objects.all()


class AreaMembersView(APIView):
    """Drill-down: miembros de un área específica."""
    permission_classes = [IsSuperAdmin]

    def get(self, request, pk):
        from apps.authentication.serializers import UserProfileSerializer
        members = User.objects.filter(area_id=pk)
        serializer = UserProfileSerializer(members, many=True)
        return Response(serializer.data)
```

### 5.4 `apps/areas/urls.py`

```python
from django.urls import path
from .views import AreaListCreateView, AreaDetailView, AreaMembersView

urlpatterns = [
    path('',                  AreaListCreateView.as_view(), name='area-list'),
    path('<int:pk>/',         AreaDetailView.as_view(),     name='area-detail'),
    path('<int:pk>/members/', AreaMembersView.as_view(),    name='area-members'),
]
```

---

## 6. App: users

### 6.1 `apps/users/serializers.py`

```python
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserListSerializer(serializers.ModelSerializer):
    area_name = serializers.CharField(source='area.name', read_only=True)
    full_name = serializers.ReadOnlyField()

    class Meta:
        model  = User
        fields = ['id', 'email', 'full_name', 'role', 'area', 'area_name']


class InviteUserSerializer(serializers.Serializer):
    email      = serializers.EmailField()
    first_name = serializers.CharField(max_length=100)
    last_name  = serializers.CharField(max_length=100)
    role       = serializers.ChoiceField(choices=User.Role.choices)
    area       = serializers.PrimaryKeyRelatedField(
        queryset=__import__('apps.areas.models', fromlist=['Area']).Area.objects.all(),
        allow_null=True, required=False
    )

    def validate(self, data):
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({'email': 'Este email ya está registrado.'})
        return data

    def create(self, validated_data):
        import secrets
        temp_password = secrets.token_urlsafe(12)
        user = User.objects.create_user(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            role=validated_data['role'],
            area=validated_data.get('area'),
            password=temp_password,
        )
        # TODO: enviar email con temp_password al nuevo usuario
        return user


class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['role', 'area']
```

### 6.2 `apps/users/views.py`

```python
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from core.permissions import IsSuperAdmin, IsAdminAreaOrAbove
from .serializers import UserListSerializer, InviteUserSerializer, UpdateUserSerializer

User = get_user_model()


class UserListView(generics.ListAPIView):
    serializer_class   = UserListSerializer
    permission_classes = [IsAdminAreaOrAbove]

    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin:
            return User.objects.all().select_related('area')
        # Admin solo ve su área
        return User.objects.filter(area=user.area).select_related('area')


class InviteUserView(APIView):
    permission_classes = [IsAdminAreaOrAbove]

    def post(self, request):
        serializer = InviteUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Admin de área solo puede invitar a su propia área
        if request.user.is_admin_area:
            if serializer.validated_data.get('area') != request.user.area:
                return Response(
                    {'detail': 'Solo puedes invitar usuarios a tu área.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        user = serializer.save()
        return Response(UserListSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsSuperAdmin]
    queryset           = User.objects.all()

    def get_serializer_class(self):
        if self.request.method in ['PATCH', 'PUT']:
            return UpdateUserSerializer
        return UserListSerializer
```

### 6.3 `apps/users/urls.py`

```python
from django.urls import path
from .views import UserListView, InviteUserView, UserDetailView

urlpatterns = [
    path('',          UserListView.as_view(),   name='user-list'),
    path('invite/',   InviteUserView.as_view(),  name='user-invite'),
    path('<int:pk>/', UserDetailView.as_view(),  name='user-detail'),
]
```

---

## 7. App: activities

> Esta es la app más crítica del sistema. Incluye signals para la bitácora automática.

### 7.1 `apps/activities/models.py`

```python
from django.db import models
from django.conf import settings


class Activity(models.Model):
    class Status(models.TextChoices):
        BANDEJA    = 'bandeja',    'Bandeja'
        HOY        = 'hoy',        'Hoy'
        MANANA     = 'manana',     'Mañana'
        PROGRAMADO = 'programado', 'Programado'
        PENDIENTES = 'pendientes', 'Pendientes'
        COMPLETADA = 'completada', 'Completada'

    title          = models.CharField(max_length=255)
    description    = models.TextField(blank=True, default='')
    status         = models.CharField(max_length=20, choices=Status.choices, default=Status.BANDEJA)

    owner          = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='owned_activities'
    )
    assigned_to    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_activities'
    )
    assigned_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='delegated_activities'
    )

    area           = models.ForeignKey(
        'areas.Area', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='activities'
    )
    project        = models.ForeignKey(
        'projects.Project', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='activities'
    )

    target_date    = models.DateField(null=True, blank=True)
    completed_at   = models.DateTimeField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'activities'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ActivityLog(models.Model):
    class EventType(models.TextChoices):
        CREATED   = 'created',   'Creada'
        MOVED     = 'moved',     'Movida'
        ASSIGNED  = 'assigned',  'Asignada'
        COMPLETED = 'completed', 'Completada'
        EDITED    = 'edited',    'Editada'
        DELETED   = 'deleted',   'Eliminada'

    activity   = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='logs')
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    detail     = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'activity_logs'
        ordering = ['-created_at']


class Attachment(models.Model):
    class Type(models.TextChoices):
        IMAGE = 'image', 'Imagen'
        FILE  = 'file',  'Archivo'

    activity   = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='attachments')
    type       = models.CharField(max_length=10, choices=Type.choices)
    file       = models.FileField(upload_to='attachments/%Y/%m/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'attachments'
```

### 7.2 `apps/activities/signals.py`

```python
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Activity, ActivityLog

# Guarda el estado previo antes de guardar
@receiver(pre_save, sender=Activity)
def capture_previous_state(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._previous = Activity.objects.get(pk=instance.pk)
        except Activity.DoesNotExist:
            instance._previous = None
    else:
        instance._previous = None


@receiver(post_save, sender=Activity)
def write_activity_log(sender, instance, created, **kwargs):
    user = getattr(instance, '_current_user', None)
    prev = getattr(instance, '_previous', None)

    if created:
        detail = {'project': instance.project.name if instance.project else None}
        ActivityLog.objects.create(
            activity=instance, user=user,
            event_type=ActivityLog.EventType.CREATED, detail=detail
        )
        return

    if prev is None:
        return

    # Detectar movimiento entre columnas
    if prev.status != instance.status:
        ActivityLog.objects.create(
            activity=instance, user=user,
            event_type=ActivityLog.EventType.MOVED,
            detail={'from': prev.status, 'to': instance.status}
        )

    # Detectar asignación
    if prev.assigned_to_id != instance.assigned_to_id:
        ActivityLog.objects.create(
            activity=instance, user=user,
            event_type=ActivityLog.EventType.ASSIGNED,
            detail={'assigned_to': instance.assigned_to.full_name if instance.assigned_to else None}
        )

    # Detectar completada
    if prev.status != 'completada' and instance.status == 'completada':
        ActivityLog.objects.create(
            activity=instance, user=user,
            event_type=ActivityLog.EventType.COMPLETED, detail={}
        )

    # Detectar edición de contenido
    if prev.title != instance.title or prev.description != instance.description:
        ActivityLog.objects.create(
            activity=instance, user=user,
            event_type=ActivityLog.EventType.EDITED,
            detail={'fields': ['title'] if prev.title != instance.title else ['description']}
        )
```

> **Cómo usar `_current_user` en las views:** antes de `instance.save()`, asignar `instance._current_user = request.user`. Esto pasa el usuario al signal sin modificar el modelo.

### 7.3 `apps/activities/apps.py`

```python
from django.apps import AppConfig


class ActivitiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.activities'

    def ready(self):
        import apps.activities.signals  # noqa: registra los signals
```

### 7.4 `apps/activities/serializers.py`

```python
from rest_framework import serializers
from .models import Activity, ActivityLog, Attachment
from django.utils import timezone


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Attachment
        fields = ['id', 'type', 'file', 'created_at']
        read_only_fields = ['id', 'created_at']


class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model  = ActivityLog
        fields = ['id', 'event_type', 'detail', 'user_name', 'created_at']


class ActivitySerializer(serializers.ModelSerializer):
    owner_name       = serializers.CharField(source='owner.full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.full_name', read_only=True)
    assigned_by_name = serializers.CharField(source='assigned_by.full_name', read_only=True)
    project_name     = serializers.CharField(source='project.name', read_only=True)
    area_name        = serializers.CharField(source='area.name', read_only=True)
    attachments      = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model  = Activity
        fields = [
            'id', 'title', 'description', 'status',
            'owner', 'owner_name',
            'assigned_to', 'assigned_to_name',
            'assigned_by', 'assigned_by_name',
            'area', 'area_name',
            'project', 'project_name',
            'target_date', 'completed_at',
            'attachments', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'owner', 'assigned_by', 'completed_at', 'created_at', 'updated_at']


class MoveActivitySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Activity.Status.choices)


class AssignActivitySerializer(serializers.Serializer):
    assigned_to = serializers.IntegerField()

    def validate_assigned_to(self, value):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(pk=value).exists():
            raise serializers.ValidationError('Usuario no encontrado.')
        return value
```

### 7.5 `apps/activities/views.py`

```python
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.auth import get_user_model
from core.permissions import IsOwnerOrAssignee, IsAdminAreaOrAbove
from .models import Activity, ActivityLog, Attachment
from .serializers import (
    ActivitySerializer, ActivityLogSerializer,
    MoveActivitySerializer, AssignActivitySerializer, AttachmentSerializer
)

User = get_user_model()


class ActivityListCreateView(generics.ListCreateAPIView):
    serializer_class = ActivitySerializer

    def get_queryset(self):
        user = self.request.user
        qs = Activity.objects.filter(
            owner=user
        ) | Activity.objects.filter(assigned_to=user)
        qs = qs.distinct().select_related('owner', 'assigned_to', 'assigned_by', 'project', 'area')

        # Filtros opcionales por query param
        status_filter = self.request.query_params.get('status')
        project_filter = self.request.query_params.get('project_id')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if project_filter:
            qs = qs.filter(project_id=project_filter)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        instance = serializer.save(
            owner=user,
            area=user.area,
        )
        instance._current_user = user


class ActivityDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class   = ActivitySerializer
    permission_classes = [IsOwnerOrAssignee]

    def get_queryset(self):
        return Activity.objects.select_related(
            'owner', 'assigned_to', 'assigned_by', 'project', 'area'
        ).prefetch_related('attachments')

    def perform_update(self, serializer):
        instance = serializer.save()
        instance._current_user = self.request.user
        instance.save()


class MoveActivityView(APIView):
    """PATCH activities/{id}/move/ — mueve entre columnas y escribe en log."""
    permission_classes = [IsOwnerOrAssignee]

    def patch(self, request, pk):
        activity = Activity.objects.get(pk=pk)
        self.check_object_permissions(request, activity)

        serializer = MoveActivitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        activity._current_user = request.user
        activity.status = serializer.validated_data['status']

        if activity.status == Activity.Status.COMPLETADA:
            activity.completed_at = timezone.now()

        activity.save()
        return Response(ActivitySerializer(activity).data)


class CompleteActivityView(APIView):
    permission_classes = [IsOwnerOrAssignee]

    def patch(self, request, pk):
        activity = Activity.objects.get(pk=pk)
        self.check_object_permissions(request, activity)

        activity._current_user = request.user
        activity.status = Activity.Status.COMPLETADA
        activity.completed_at = timezone.now()
        activity.save()
        return Response(ActivitySerializer(activity).data)


class AssignActivityView(APIView):
    permission_classes = [IsAdminAreaOrAbove]

    def patch(self, request, pk):
        activity = Activity.objects.get(pk=pk)
        serializer = AssignActivitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assignee = User.objects.get(pk=serializer.validated_data['assigned_to'])

        # Admin de área solo puede asignar a miembros de su área
        if request.user.is_admin_area and assignee.area != request.user.area:
            return Response(
                {'detail': 'Solo puedes asignar a miembros de tu área.'},
                status=status.HTTP_403_FORBIDDEN
            )

        activity._current_user = request.user
        activity.assigned_to = assignee
        activity.assigned_by = request.user
        activity.save()
        return Response(ActivitySerializer(activity).data)


class ActivityLogView(generics.ListAPIView):
    serializer_class   = ActivityLogSerializer
    permission_classes = [IsOwnerOrAssignee]

    def get_queryset(self):
        return ActivityLog.objects.filter(activity_id=self.kwargs['pk'])


class AttachmentCreateView(APIView):
    permission_classes = [IsOwnerOrAssignee]

    def post(self, request, pk):
        activity = Activity.objects.get(pk=pk)
        self.check_object_permissions(request, activity)

        serializer = AttachmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(activity=activity)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AttachmentDeleteView(APIView):
    permission_classes = [IsOwnerOrAssignee]

    def delete(self, request, pk, att_id):
        attachment = Attachment.objects.get(pk=att_id, activity_id=pk)
        attachment.file.delete(save=False)
        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
```

### 7.6 `apps/activities/urls.py`

```python
from django.urls import path
from .views import (
    ActivityListCreateView, ActivityDetailView,
    MoveActivityView, CompleteActivityView, AssignActivityView,
    ActivityLogView, AttachmentCreateView, AttachmentDeleteView,
)

urlpatterns = [
    path('',                               ActivityListCreateView.as_view(), name='activity-list'),
    path('<int:pk>/',                      ActivityDetailView.as_view(),     name='activity-detail'),
    path('<int:pk>/move/',                 MoveActivityView.as_view(),       name='activity-move'),
    path('<int:pk>/complete/',             CompleteActivityView.as_view(),   name='activity-complete'),
    path('<int:pk>/assign/',               AssignActivityView.as_view(),     name='activity-assign'),
    path('<int:pk>/log/',                  ActivityLogView.as_view(),        name='activity-log'),
    path('<int:pk>/attachments/',          AttachmentCreateView.as_view(),   name='attachment-create'),
    path('<int:pk>/attachments/<int:att_id>/', AttachmentDeleteView.as_view(), name='attachment-delete'),
]
```

---

## 8. App: projects

### 8.1 `apps/projects/models.py`

```python
from django.db import models
from django.conf import settings


class Project(models.Model):
    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    color       = models.CharField(max_length=7, default='#378ADD')  # hex color
    owner       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='owned_projects'
    )
    area        = models.ForeignKey(
        'areas.Area', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='projects'
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'projects'
        ordering = ['-created_at']

    @property
    def total_activities(self):
        return self.activities.count()

    @property
    def completed_activities(self):
        return self.activities.filter(status='completada').count()

    def __str__(self):
        return self.name
```

### 8.2 `apps/projects/serializers.py`

```python
from rest_framework import serializers
from .models import Project


class ProjectSerializer(serializers.ModelSerializer):
    owner_name         = serializers.CharField(source='owner.full_name', read_only=True)
    area_name          = serializers.CharField(source='area.name', read_only=True)
    total_activities   = serializers.ReadOnlyField()
    completed_activities = serializers.ReadOnlyField()

    class Meta:
        model  = Project
        fields = [
            'id', 'name', 'description', 'color',
            'owner', 'owner_name', 'area', 'area_name',
            'total_activities', 'completed_activities', 'created_at',
        ]
        read_only_fields = ['id', 'owner', 'created_at']
```

### 8.3 `apps/projects/views.py`

```python
from rest_framework import generics
from core.permissions import IsAdminAreaOrAbove
from .models import Project
from .serializers import ProjectSerializer


class ProjectListCreateView(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin:
            return Project.objects.all().select_related('owner', 'area')
        if user.is_admin_area:
            return Project.objects.filter(area=user.area).select_related('owner', 'area')
        # Trabajador: solo sus propios proyectos
        return Project.objects.filter(owner=user).select_related('owner', 'area')

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(owner=user, area=user.area if not user.is_super_admin else None)


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return Project.objects.select_related('owner', 'area').prefetch_related('activities')

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if request.method in ['PATCH', 'PUT', 'DELETE']:
            if not (request.user.is_super_admin or
                    request.user.is_admin_area or
                    obj.owner == request.user):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied()
```

### 8.4 `apps/projects/urls.py`

```python
from django.urls import path
from .views import ProjectListCreateView, ProjectDetailView

urlpatterns = [
    path('',          ProjectListCreateView.as_view(), name='project-list'),
    path('<int:pk>/', ProjectDetailView.as_view(),     name='project-detail'),
]
```

---

## 9. App: stats

> Esta app no tiene modelos propios. Solo hace queries de agregación sobre las otras apps.

### 9.1 `apps/stats/views.py`

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Count, Q
from core.permissions import IsAdminAreaOrAbove
from apps.activities.models import Activity


def activity_summary(queryset):
    """Resumen de actividades por estado para un queryset dado."""
    today = timezone.now().date()
    week_start = today - timezone.timedelta(days=today.weekday())

    total = queryset.count()
    completed_today = queryset.filter(
        status='completada',
        completed_at__date=today
    ).count()
    completed_week = queryset.filter(
        status='completada',
        completed_at__date__gte=week_start
    ).count()

    by_status = queryset.values('status').annotate(count=Count('id'))
    status_map = {item['status']: item['count'] for item in by_status}

    return {
        'total': total,
        'completed_today': completed_today,
        'completed_week': completed_week,
        'by_status': status_map,
    }


class MyStatsView(APIView):
    def get(self, request):
        qs = Activity.objects.filter(
            Q(owner=request.user) | Q(assigned_to=request.user)
        ).distinct()
        return Response(activity_summary(qs))


class AreaStatsView(APIView):
    permission_classes = [IsAdminAreaOrAbove]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        area = request.user.area
        members = User.objects.filter(area=area)
        member_stats = []

        for member in members:
            qs = Activity.objects.filter(
                Q(owner=member) | Q(assigned_to=member)
            ).distinct()
            member_stats.append({
                'user_id': member.id,
                'user_name': member.full_name,
                **activity_summary(qs),
            })

        area_qs = Activity.objects.filter(area=area)
        return Response({
            'area_summary': activity_summary(area_qs),
            'members': member_stats,
        })


class AreaDrillDownView(APIView):
    """Solo Super Admin: ver stats de un área específica."""
    permission_classes = [IsAdminAreaOrAbove]

    def get(self, request, area_id):
        if not request.user.is_super_admin:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()

        from apps.areas.models import Area
        from django.contrib.auth import get_user_model
        User = get_user_model()

        area = Area.objects.get(pk=area_id)
        members = User.objects.filter(area=area)
        member_stats = []

        for member in members:
            qs = Activity.objects.filter(
                Q(owner=member) | Q(assigned_to=member)
            ).distinct()
            member_stats.append({
                'user_id': member.id,
                'user_name': member.full_name,
                **activity_summary(qs),
            })

        area_qs = Activity.objects.filter(area=area)
        return Response({
            'area': {'id': area.id, 'name': area.name},
            'area_summary': activity_summary(area_qs),
            'members': member_stats,
        })
```

### 9.2 `apps/stats/urls.py`

```python
from django.urls import path
from .views import MyStatsView, AreaStatsView, AreaDrillDownView

urlpatterns = [
    path('me/',              MyStatsView.as_view(),          name='stats-me'),
    path('area/',            AreaStatsView.as_view(),         name='stats-area'),
    path('area/<int:area_id>/', AreaDrillDownView.as_view(), name='stats-area-detail'),
]
```

---

## 10. Logging

### 10.1 Configuración en `config/settings/base.py`

```python
import os

# Crear directorio de logs si no existe
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{asctime}] {levelname} {message}',
            'style': '{',
        },
    },

    'handlers': {
        'django_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'django.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'security_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'security.log',
            'maxBytes': 5 * 1024 * 1024,   # 5 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'errors.log',
            'maxBytes': 5 * 1024 * 1024,   # 5 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },

    'loggers': {
        'django': {
            'handlers': ['django_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        # Logger propio para el proyecto
        'productivity': {
            'handlers': ['django_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}
```

### 10.2 Uso del logger en las views

```python
import logging
logger = logging.getLogger('productivity')

# En cualquier view:
logger.info(f'Actividad {activity.id} movida a {new_status} por usuario {request.user.id}')
logger.warning(f'Intento de asignación fuera de área: user={request.user.id}')
logger.error(f'Error al subir adjunto: {str(e)}')
```

---

## 11. Rate limiting

### 11.1 Instalación

```bash
pip install django-ratelimit
```

Agregar a `INSTALLED_APPS` en `base.py`:

```python
'django_ratelimit',
```

### 11.2 Aplicar en views críticas

```python
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

# En auth/views.py — login
@method_decorator(ratelimit(key='ip', rate='5/m', method='POST', block=True), name='dispatch')
class LoginView(TokenObtainPairView):
    pass

# En users/views.py — invitaciones
@method_decorator(ratelimit(key='user', rate='10/h', method='POST', block=True), name='dispatch')
class InviteUserView(APIView):
    ...

# En activities/views.py — creación
@method_decorator(ratelimit(key='user', rate='60/m', method='POST', block=True), name='dispatch')
class ActivityListCreateView(generics.ListCreateAPIView):
    ...

# En stats/views.py
@method_decorator(ratelimit(key='user', rate='30/m', method='GET', block=True), name='dispatch')
class MyStatsView(APIView):
    ...
```

### 11.3 Tabla de límites por endpoint

| Endpoint | Límite | Clave |
|---|---|---|
| `auth/login/` | 5 / minuto | IP |
| `auth/refresh/` | 20 / minuto | IP |
| `users/invite/` | 10 / hora | usuario |
| `activities/` POST | 60 / minuto | usuario |
| `attachments/` POST | 20 / hora | usuario |
| `stats/` GET | 30 / minuto | usuario |

---

## 12. Docker y docker-compose

### 12.1 `Dockerfile`

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python
COPY requirements/production.txt .
RUN pip install --no-cache-dir -r production.txt

# Código del proyecto
COPY . .

# Crear directorios necesarios
RUN mkdir -p logs media staticfiles

# Recopilar archivos estáticos
RUN python manage.py collectstatic --noinput \
    --settings=config.settings.production || true

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "logs/gunicorn_access.log", \
     "--error-logfile", "logs/gunicorn_error.log"]
```

### 12.2 `docker-compose.yml`

```yaml
version: '3.9'

services:

  db:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    build: .
    restart: unless-stopped
    env_file: .env
    environment:
      DJANGO_SETTINGS_MODULE: config.settings.production
    volumes:
      - ./logs:/app/logs
      - ./media:/app/media
    depends_on:
      db:
        condition: service_healthy
    expose:
      - "8000"

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
      - ./media:/media:ro
      - ./staticfiles:/staticfiles:ro
    depends_on:
      - web

volumes:
  postgres_data:
```

### 12.3 Comandos Docker útiles

```bash
# Levantar todo
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f web

# Correr migraciones dentro del contenedor
docker-compose exec web python manage.py migrate

# Crear superusuario
docker-compose exec web python manage.py createsuperuser

# Reconstruir imagen después de cambios en requirements
docker-compose up -d --build

# Bajar todo
docker-compose down

# Bajar y eliminar volúmenes (cuidado: borra la DB)
docker-compose down -v
```

---

## 13. Nginx y Gunicorn

### 13.1 `nginx/nginx.conf`

```nginx
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    sendfile      on;
    keepalive_timeout 65;

    # Limitar tamaño de archivos subidos
    client_max_body_size 20M;

    # Rate limiting a nivel Nginx (complementa django-ratelimit)
    limit_req_zone $binary_remote_addr zone=api:10m rate=30r/m;
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;

    upstream django {
        server web:8000;
    }

    server {
        listen 80;
        server_name tu-dominio.com;

        # Redirigir todo a HTTPS
        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl;
        server_name tu-dominio.com;

        ssl_certificate     /etc/nginx/certs/fullchain.pem;
        ssl_certificate_key /etc/nginx/certs/privkey.pem;
        ssl_protocols       TLSv1.2 TLSv1.3;
        ssl_ciphers         HIGH:!aNULL:!MD5;

        # Headers de seguridad
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

        # Archivos estáticos
        location /static/ {
            alias /staticfiles/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }

        # Archivos media (adjuntos)
        location /media/ {
            alias /media/;
            expires 7d;
        }

        # Rate limit en login
        location /api/auth/login/ {
            limit_req zone=login burst=3 nodelay;
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # API general
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://django;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 90;
        }
    }
}
```

---

## 14. Variables de entorno

### 14.1 `.env.example`

```bash
# Django
SECRET_KEY=
DEBUG=False
ALLOWED_HOSTS=tu-dominio.com
DJANGO_SETTINGS_MODULE=config.settings.production

# Base de datos
DB_NAME=productivity_db
DB_USER=productivity_user
DB_PASSWORD=
DB_HOST=db
DB_PORT=5432

# JWT
JWT_ACCESS_TOKEN_LIFETIME=60
JWT_REFRESH_TOKEN_LIFETIME=7

# CORS — separar con comas si hay varios orígenes
CORS_ALLOWED_ORIGINS=https://tu-dominio.com
```

> Copiar como `.env` y completar los valores reales. **Nunca subir `.env` al repositorio.**

### 14.2 `.gitignore` mínimo

```
.env
__pycache__/
*.pyc
*.pyo
db.sqlite3
media/
staticfiles/
logs/
venv/
.DS_Store
```

---

## 15. Router principal

### 15.1 `config/urls.py`

```python
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

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## 16. Checklist de despliegue

### Primera vez en servidor propio

```bash
# 1. Clonar el repositorio
git clone <repo-url> && cd productivity_backend

# 2. Copiar y completar variables de entorno
cp .env.example .env
nano .env

# 3. Crear directorio de certificados SSL
mkdir -p nginx/certs
# Copiar fullchain.pem y privkey.pem de Cloudflare o Let's Encrypt

# 4. Levantar servicios
docker-compose up -d

# 5. Correr migraciones
docker-compose exec web python manage.py migrate

# 6. Crear superusuario inicial (Super Admin)
docker-compose exec web python manage.py createsuperuser

# 7. Verificar logs
docker-compose logs web
tail -f logs/django.log
```

### Actualización de código

```bash
git pull origin main
docker-compose up -d --build
docker-compose exec web python manage.py migrate
```

### Cuando saltes a AWS

- Reemplazar el servicio `db` por **RDS PostgreSQL**
- Reemplazar `media/` local por **S3** con `django-storages`
- Usar **ECR** para las imágenes Docker
- Desplegar en **ECS Fargate** o **EC2** con el mismo `docker-compose.yml`
- Configurar **CloudWatch** para los logs en lugar de archivos locales

---

## 17. Invitaciones por link

### 17.1 Modelo

```python
# apps/authentication/models.py  (agregar junto a User)
import uuid
from django.utils import timezone
from datetime import timedelta

class Invitation(models.Model):
    token       = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    email       = models.EmailField()
    role        = models.CharField(max_length=20, choices=User.Role.choices)
    area        = models.ForeignKey(
        'areas.Area', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    invited_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='sent_invitations'
    )
    expires_at  = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'invitations'

    @property
    def is_valid(self):
        return self.accepted_at is None and self.expires_at > timezone.now()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Invitación para {self.email} ({self.role})'
```

### 17.2 Serializers

```python
# apps/authentication/serializers.py (agregar)
from .models import Invitation
from django.conf import settings

class SendInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Invitation
        fields = ['email', 'role', 'area']

    def validate(self, data):
        request = self.context['request']
        # Admin de área solo puede invitar a su propia área
        if request.user.is_admin_area:
            if data.get('area') != request.user.area:
                raise serializers.ValidationError(
                    'Solo puedes invitar usuarios a tu área.'
                )
            if data['role'] not in ['trabajador']:
                raise serializers.ValidationError(
                    'Solo puedes invitar trabajadores.'
                )
        return data

    def create(self, validated_data):
        return Invitation.objects.create(
            **validated_data,
            invited_by=self.context['request'].user
        )


class InvitationDetailSerializer(serializers.ModelSerializer):
    invited_by_name = serializers.CharField(source='invited_by.full_name', read_only=True)
    area_name       = serializers.CharField(source='area.name', read_only=True)
    is_valid        = serializers.ReadOnlyField()

    class Meta:
        model  = Invitation
        fields = ['token', 'email', 'role', 'area', 'area_name',
                  'invited_by_name', 'expires_at', 'is_valid', 'created_at']


class AcceptInvitationSerializer(serializers.Serializer):
    token      = serializers.UUIDField()
    first_name = serializers.CharField(max_length=100)
    last_name  = serializers.CharField(max_length=100)
    password   = serializers.CharField(min_length=8, write_only=True)

    def validate_token(self, value):
        try:
            invitation = Invitation.objects.get(token=value)
        except Invitation.DoesNotExist:
            raise serializers.ValidationError('Link inválido.')
        if not invitation.is_valid:
            raise serializers.ValidationError('Este link ya fue usado o expiró.')
        return value

    def create(self, validated_data):
        from django.utils import timezone
        invitation = Invitation.objects.get(token=validated_data['token'])

        # Crear usuario con el rol y área de la invitación
        user = User.objects.create_user(
            email=invitation.email,
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password'],
            role=invitation.role,
            area=invitation.area,
        )

        # Marcar invitación como usada (un solo uso)
        invitation.accepted_at = timezone.now()
        invitation.save()

        return user
```

### 17.3 Views

```python
# apps/authentication/views.py (agregar)
from .models import Invitation
from .serializers import SendInvitationSerializer, InvitationDetailSerializer, AcceptInvitationSerializer
from core.permissions import IsAdminAreaOrAbove
from rest_framework_simplejwt.tokens import RefreshToken as JWTRefreshToken

class SendInvitationView(APIView):
    """SA o Admin genera el link — el invitador lo copia y manda por WhatsApp u otro medio."""
    permission_classes = [IsAdminAreaOrAbove]

    def post(self, request):
        serializer = SendInvitationSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        invitation = serializer.save()

        # Construir el link — Flutter lo abre con deep link
        base_url = request.build_absolute_uri('/').rstrip('/')
        link = f"{base_url}/invite/{invitation.token}"

        return Response({
            'link': link,
            'expires_at': invitation.expires_at,
            'email': invitation.email,
            'role': invitation.role,
        }, status=status.HTTP_201_CREATED)


class RegenerateInvitationView(APIView):
    """Regenerar link expirado — crea una nueva invitación para el mismo email/rol/área."""
    permission_classes = [IsAdminAreaOrAbove]

    def post(self, request, pk):
        try:
            old = Invitation.objects.get(pk=pk, invited_by=request.user)
        except Invitation.DoesNotExist:
            return Response({'detail': 'No encontrada.'}, status=404)

        if old.accepted_at:
            return Response(
                {'detail': 'Esta invitación ya fue aceptada, no se puede regenerar.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Invalidar la anterior y crear nueva
        old.expires_at = timezone.now()
        old.save()

        new_inv = Invitation.objects.create(
            email=old.email, role=old.role,
            area=old.area, invited_by=request.user
        )
        base_url = request.build_absolute_uri('/').rstrip('/')
        link = f"{base_url}/invite/{new_inv.token}"

        return Response({'link': link, 'expires_at': new_inv.expires_at})


class ValidateInvitationView(APIView):
    """Flutter llama esto antes de mostrar el formulario de registro."""
    permission_classes = []  # público — solo valida el token

    def get(self, request, token):
        try:
            invitation = Invitation.objects.get(token=token)
        except Invitation.DoesNotExist:
            return Response({'valid': False, 'detail': 'Link inválido.'}, status=404)

        if not invitation.is_valid:
            return Response({'valid': False, 'detail': 'Link expirado o ya usado.'}, status=400)

        return Response(InvitationDetailSerializer(invitation).data)


class AcceptInvitationView(APIView):
    """Usuario nuevo completa su registro usando el token del link."""
    permission_classes = []  # público

    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Devolver JWT directo para que el usuario quede logueado
        refresh = JWTRefreshToken.for_user(user)
        return Response({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': user.id,
                'full_name': user.full_name,
                'email': user.email,
                'role': user.role,
            }
        }, status=status.HTTP_201_CREATED)
```

### 17.4 URLs

```python
# apps/authentication/urls.py (agregar)
from .views import (
    SendInvitationView, RegenerateInvitationView,
    ValidateInvitationView, AcceptInvitationView
)

urlpatterns += [
    path('invitations/send/',              SendInvitationView.as_view(),      name='invite-send'),
    path('invitations/<int:pk>/regenerate/', RegenerateInvitationView.as_view(), name='invite-regenerate'),
    path('invitations/<uuid:token>/',      ValidateInvitationView.as_view(),  name='invite-validate'),
    path('invitations/accept/',            AcceptInvitationView.as_view(),    name='invite-accept'),
]
```

### 17.5 Migración

```bash
python manage.py makemigrations authentication
python manage.py migrate
```

### 17.6 Reglas de negocio del link

| Regla | Valor |
|---|---|
| Validez del link | 24 horas desde creación |
| Usos permitidos | 1 solo uso — se invalida al aceptar |
| Regenerable | Sí — el invitador puede generar uno nuevo |
| Distribución | Copiado manualmente — WhatsApp, email, cualquier medio |
| Formato | `https://tu-dominio.com/invite/{uuid}` |
| Flutter lo abre con | Deep link — `app://invite/{uuid}` |

---

## 18. Onboarding y pantalla de bienvenida

### 18.1 Flujo completo

```
Abre la app
  │
  ├── ¿Tiene JWT en SecureStorage?
  │     │
  │     ├── No → Pantalla de Login
  │     │         ├── ¿Tiene cuenta? No → Registro (email, nombre, contraseña)
  │     │         │                         → Verificación de email (código 6 dígitos)
  │     │         │                         → Pantalla de bienvenida
  │     │         │                         → Tablero
  │     │         └── ¿Tiene cuenta? Sí → Login normal
  │     │                                   → Pantalla de bienvenida (solo 1ra vez)
  │     │                                   → Tablero
  │     │
  │     └── Sí → Pide biometría / PIN
  │               ├── OK  → Libera JWT → Tablero
  │               └── Falla → Bloquea (3 intentos → logout forzado)
  │
  └── ¿Abre desde link de invitación?
        → Valida token con backend
        → Formulario de registro pre-llenado (email bloqueado, rol asignado)
        → Registro → JWT directo → Pantalla de bienvenida → Tablero
```

### 18.2 Pantalla de bienvenida

Se muestra **una sola vez** tras el primer login o registro exitoso. Se marca en local (`SharedPreferences`) como `onboarding_completed = true`.

Contenido sugerido por pantalla (slides):

| Slide | Título | Descripción |
|---|---|---|
| 1 | Bienvenido a [nombre app] | Tu sistema de productividad personal y de equipo |
| 2 | Captura todo | Guarda cualquier tarea en tu bandeja antes de perderla |
| 3 | Organiza tu día | Mueve actividades a Hoy, Mañana o Programado según tu ritmo |
| 4 | Proyectos grandes | Desglosa proyectos en actividades manejables con su propio tablero |
| 5 | Tu equipo (si aplica) | Recibe y asigna actividades dentro de tu área |

Último slide tiene botón **"Comenzar"** que lleva al Tablero.

### 18.3 Campo nuevo en User para tracking de onboarding

```python
# Agregar a apps/authentication/models.py → clase User
onboarding_completed = models.BooleanField(default=False)
```

El backend lo expone en `GET /api/auth/me/` para que Flutter sepa si debe mostrar la bienvenida o ir directo al tablero en futuros logins.

---

## 19. Seguridad biométrica (Flutter — documentado para implementación)

> La biometría es una capa **local** en Flutter. El backend no cambia — sigue recibiendo JWT normalmente. Lo que cambia es que Flutter no libera el JWT hasta que la biometría o PIN es validado.

### 19.1 Flujo de seguridad local

```
Login exitoso
  → backend devuelve JWT
  → Flutter guarda JWT cifrado en flutter_secure_storage
  → App activa flag biometría_configurada = true

Siguiente apertura de app
  → Flutter lee flutter_secure_storage
  → Si hay JWT guardado → solicita biometría al SO (local_auth)
      → Biometría OK  → entrega JWT a la capa HTTP → requests al backend
      → Biometría fail → contador de intentos++
          → 3 intentos fallidos → borra JWT → logout forzado → pantalla login
  → Si no hay JWT → pantalla login normal
```

### 19.2 Fallback a PIN

Si el dispositivo no tiene biometría configurada:

```
flutter_secure_storage detecta biometría no disponible
  → solicita crear PIN de 4-6 dígitos (primer login)
  → PIN se guarda cifrado en flutter_secure_storage
  → en aperturas siguientes → pide PIN en lugar de biometría
```

### 19.3 Paquetes Flutter necesarios

```yaml
# pubspec.yaml
dependencies:
  local_auth: ^2.1.8           # biometría (Face ID, huella)
  flutter_secure_storage: ^9.0.0  # almacenamiento cifrado del JWT
  shared_preferences: ^2.2.0   # flags ligeros (onboarding_completed, etc.)
```

### 19.4 Consideraciones de seguridad

- El JWT **nunca** vive en memoria hasta que la biometría es aprobada
- En iOS usa el Keychain, en Android usa el Keystore — ambos son cifrado a nivel hardware
- Si el usuario desinstala la app, el SecureStorage se borra (iOS) o puede persistir (Android) — contemplar este caso en el logout
- El backend no tiene conocimiento de si el dispositivo tiene biometría — la seguridad es completamente del lado del cliente

---

*Productivity App · Tree Tech Solutions · 2026*
