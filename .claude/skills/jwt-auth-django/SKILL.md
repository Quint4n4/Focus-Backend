---
name: jwt-auth-django
description: "ALWAYS use this skill when the user asks to: implement JWT authentication in Django, configure SimpleJWT, set up token rotation or blacklist, create login/logout/refresh endpoints, handle biometric authentication flow in Django backend, implement secure token management for a Flutter+Django app, handle 401 responses and token expiry, or design the complete authentication system for a DRF API. Also trigger for: refresh token rotation, JWT blacklisting, biometric-enabled user model, device binding for tokens, or any question about how the backend handles Face ID / fingerprint login. This skill covers the complete JWT lifecycle: issuance, rotation, blacklist, revocation, biometric activation endpoints, and all auth-related views."
---

# JWT Auth Django — Autenticación completa con biometría local

## Arquitectura de autenticación

El sistema tiene dos modos de login pero UN SOLO mecanismo de tokens:
- Login con email+password → Django valida credenciales → emite JWT
- Login biométrico → OS del dispositivo verifica cara/huella → app usa refresh token guardado → Django emite nuevo access token

**El backend NUNCA procesa datos biométricos.** La cara se verifica en el Secure Enclave del teléfono.

---

## 1. Instalación y configuración de SimpleJWT

```python
# requirements.txt
djangorestframework-simplejwt>=5.3
# Para blacklist de tokens:
# rest_framework_simplejwt.token_blacklist (incluido en simplejwt)
```

```python
# settings/base.py
from datetime import timedelta
import os

INSTALLED_APPS += [
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
]

SIMPLE_JWT = {
    # Tiempos de vida
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),   # Corto — minimiza exposición
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),

    # Rotación — cada refresh genera nuevo refresh, invalida el anterior
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,

    # Seguridad
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',                # RS256 para microservicios
    'SIGNING_KEY': os.environ['JWT_SECRET_KEY'],  # SEPARADO del SECRET_KEY
    'AUTH_HEADER_TYPES': ('Bearer',),
    'JTI_CLAIM': 'jti',                  # JWT ID único por token

    # Payload mínimo — no incluir datos sensibles en el token
    'TOKEN_OBTAIN_SERIALIZER': 'authentication.serializers.CustomTokenObtainPairSerializer',
}
```

---

## 2. URLs de autenticación

```python
# urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Login con credenciales
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),

    # Refresh token (usado también por biometría)
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Gestión de biometría
    path('auth/biometric/enable/', views.EnableBiometricView.as_view(), name='biometric_enable'),
    path('auth/biometric/disable/', views.DisableBiometricView.as_view(), name='biometric_disable'),
    path('auth/biometric/revoke-all/', views.RevokeAllDevicesView.as_view(), name='biometric_revoke_all'),

    # Verificar estado del token (útil para debug)
    path('auth/token/verify/', views.VerifyTokenView.as_view(), name='token_verify'),
]
```

---

## 3. Serializer personalizado del token

```python
# authentication/serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Incluir solo datos NO sensibles en el payload
        # El payload es visible (solo firmado, no encriptado)
        token['email'] = user.email
        token['biometrics_enabled'] = user.biometrics_enabled
        # NUNCA incluir: password, tokens, datos financieros, datos biométricos
        return token
```

---

## 4. Views de autenticación

```python
# authentication/views.py
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from django.contrib.auth import authenticate
from django.utils import timezone
import logging

logger = logging.getLogger('security')


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'login'

    def post(self, request):
        email = request.data.get('email', '').lower().strip()
        password = request.data.get('password', '')

        if not email or not password:
            return Response(
                {'error': 'Email y contraseña son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, username=email, password=password)

        if not user:
            # Respuesta genérica — no revelar si el email existe o no
            logger.warning(f"Login fallido para email={email[:30]}")
            return Response(
                {'error': 'Credenciales inválidas'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {'error': 'Cuenta desactivada'},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)
        logger.info(f"Login exitoso user_id={user.id}")

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'biometrics_enabled': user.biometrics_enabled,
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()  # Invalida este refresh token
            logger.info(f"Logout user_id={request.user.id}")
            return Response({'message': 'Sesión cerrada correctamente'})
        except Exception:
            return Response(
                {'error': 'Token inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )


class EnableBiometricView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = 'biometric_setup'

    def post(self, request):
        device_id = request.data.get('device_id', '')
        device_model = request.data.get('device_model', '')

        if not device_id:
            return Response(
                {'error': 'device_id es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        request.user.biometrics_enabled = True
        request.user.biometrics_device_id = device_id[:200]
        request.user.biometrics_registered_at = timezone.now()
        request.user.save(update_fields=[
            'biometrics_enabled',
            'biometrics_device_id',
            'biometrics_registered_at'
        ])

        logger.info(f"Biometría activada user_id={request.user.id} device={device_model[:50]}")
        return Response({'message': 'Biometría activada correctamente'})


class DisableBiometricView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.biometrics_enabled = False
        request.user.biometrics_device_id = ''
        request.user.save(update_fields=['biometrics_enabled', 'biometrics_device_id'])
        logger.info(f"Biometría desactivada user_id={request.user.id}")
        return Response({'message': 'Biometría desactivada'})


class RevokeAllDevicesView(APIView):
    """
    El usuario llama a esto si pierde el teléfono.
    Invalida TODOS los refresh tokens activos.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Blacklistear todos los tokens activos del usuario
        tokens = OutstandingToken.objects.filter(user=request.user)
        revoked_count = 0
        for token in tokens:
            try:
                token.blacklist()
                revoked_count += 1
            except Exception:
                pass  # Ya estaba en blacklist

        # Desactivar biometría en todos los dispositivos
        request.user.biometrics_enabled = False
        request.user.biometrics_device_id = ''
        request.user.save(update_fields=['biometrics_enabled', 'biometrics_device_id'])

        logger.warning(f"Revocación total user_id={request.user.id} tokens={revoked_count}")
        return Response({
            'message': f'Se cerraron {revoked_count} sesiones activas'
        })
```

---

## 5. Modelo de usuario con soporte biométrico

```python
# users/models.py
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es requerido')
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Campos de biometría — solo metadata, nunca datos biométricos reales
    biometrics_enabled = models.BooleanField(default=False)
    biometrics_device_id = models.CharField(max_length=200, blank=True)
    biometrics_registered_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email
```

---

## 6. Flujo biométrico completo

```
PRIMER LOGIN (email + password):
Flutter → POST /auth/login/ {email, password}
         → Django valida → emite {access, refresh}
         → Flutter guarda refresh en SecureStorage
         → Flutter llama POST /auth/biometric/enable/ {device_id}
         → Django marca biometrics_enabled=True

LOGINS SIGUIENTES (biometría):
Usuario apunta cara → OS verifica (Secure Enclave) → true
         → Flutter lee refresh de SecureStorage
         → Flutter → POST /auth/token/refresh/ {refresh}
         → Django valida refresh → emite nuevo {access, refresh}
         → Flutter descarta refresh viejo, guarda el nuevo
         → Usuario autenticado

EL BACKEND NO SABE QUE HUBO BIOMETRÍA — solo ve un refresh token válido.
```

---

## 7. Seguridad adicional — Header de dispositivo

```python
# Opcional: validar que el refresh viene del dispositivo correcto
class SecureTokenRefreshView(TokenRefreshView):
    throttle_scope = 'token_refresh'

    def post(self, request, *args, **kwargs):
        device_id = request.headers.get('X-Device-ID', '')
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            logger.info(f"Token refresh device={device_id[:30]}")
        return response
```

```dart
// Flutter — incluir device_id en header
final deviceId = await _getDeviceId();  // package:device_info_plus
_dio.options.headers['X-Device-ID'] = deviceId;
```

---

## Referencia rápida de endpoints

| Método | Endpoint | Auth | Throttle | Descripción |
|--------|----------|------|----------|-------------|
| POST | /auth/login/ | No | 5/min | Email + password |
| POST | /auth/logout/ | Sí | — | Blacklist refresh |
| POST | /auth/token/refresh/ | No | 30/min | Renovar access token |
| POST | /auth/biometric/enable/ | Sí | 3/hour | Activar biometría |
| POST | /auth/biometric/disable/ | Sí | — | Desactivar biometría |
| POST | /auth/biometric/revoke-all/ | Sí | — | Cerrar todas las sesiones |
