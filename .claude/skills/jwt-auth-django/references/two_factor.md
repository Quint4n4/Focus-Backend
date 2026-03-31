# Doble Factor de Autenticación (2FA) con TOTP — Referencia Completa

## Instalación

```bash
pip install django-two-factor-auth django-otp qrcode pillow
```

## Configuración

```python
# settings/base.py
INSTALLED_APPS += [
    'django_otp',
    'django_otp.plugins.otp_totp',
    'django_otp.plugins.otp_static',
    'two_factor',
]

MIDDLEWARE += [
    'django_otp.middleware.OTPMiddleware',
]

TWO_FACTOR_PATCH_ADMIN = True
LOGIN_URL = 'two_factor:login'
```

## Flujo 2FA para API REST (Flutter)

El 2FA en una API REST tiene un flujo en dos pasos.
El cliente primero obtiene un token temporal, luego lo confirma con el código TOTP.

```python
# apps/authentication/serializers.py
from django_otp.plugins.otp_totp.models import TOTPDevice
import pyotp

class TOTPVerifySerializer(serializers.Serializer):
    temp_token = serializers.CharField()
    totp_code = serializers.CharField(min_length=6, max_length=6)

    def validate(self, data):
        # Verificar temp_token y obtener usuario
        # Verificar el código TOTP contra el dispositivo registrado
        pass
```

```python
# apps/authentication/views.py

class LoginStep1View(APIView):
    """
    Paso 1: Validar email + password.
    Si el usuario tiene 2FA, devolver temp_token en lugar de JWT.
    Si no tiene 2FA, devolver JWT completo.
    """
    permission_classes = [AllowAny]
    throttle_scope = 'login'

    def post(self, request):
        from django.contrib.auth import authenticate
        user = authenticate(
            request,
            email=request.data.get('email'),
            password=request.data.get('password'),
        )

        if not user:
            return Response({'error': 'Credenciales inválidas'}, status=401)

        # Verificar si tiene 2FA activo
        devices = TOTPDevice.objects.filter(user=user, confirmed=True)
        if devices.exists():
            # Emitir token temporal (5 minutos) para el paso 2
            from django.core.signing import TimestampSigner
            signer = TimestampSigner()
            temp_token = signer.sign(str(user.id))
            return Response({
                'requires_2fa': True,
                'temp_token': temp_token,
            })

        # Sin 2FA: emitir JWT completo
        refresh = RefreshToken.for_user(user)
        return Response({
            'requires_2fa': False,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class LoginStep2TOTPView(APIView):
    """
    Paso 2: Verificar código TOTP con el temp_token del paso 1.
    """
    permission_classes = [AllowAny]
    throttle_scope = 'login'

    def post(self, request):
        from django.core.signing import TimestampSigner, SignatureExpired, BadSignature

        temp_token = request.data.get('temp_token')
        totp_code = request.data.get('totp_code', '')

        try:
            signer = TimestampSigner()
            user_id = signer.unsign(temp_token, max_age=300)  # 5 minutos
        except (SignatureExpired, BadSignature):
            return Response({'error': 'Token expirado o inválido'}, status=401)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'Usuario no encontrado'}, status=401)

        # Verificar código TOTP
        devices = TOTPDevice.objects.filter(user=user, confirmed=True)
        verified = any(device.verify_token(totp_code) for device in devices)

        if not verified:
            return Response({'error': 'Código 2FA incorrecto'}, status=401)

        # Código correcto: emitir JWT completo
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class Setup2FAView(APIView):
    """Generar QR para que el usuario configure su app de autenticación."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Devolver URI para configurar app (Google Authenticator, Authy, etc.)"""
        device, created = TOTPDevice.objects.get_or_create(
            user=request.user,
            name='default',
            defaults={'confirmed': False}
        )

        # Generar URI compatible con apps de autenticación
        totp = pyotp.TOTP(device.bin_key_b32)
        uri = totp.provisioning_uri(
            name=request.user.email,
            issuer_name='Tu App'
        )

        return Response({
            'uri': uri,
            'secret': device.bin_key_b32,  # Para apps que no escanean QR
        })

    def post(self, request):
        """Confirmar que el usuario configuró correctamente la app."""
        code = request.data.get('code', '')
        try:
            device = TOTPDevice.objects.get(user=request.user, name='default')
        except TOTPDevice.DoesNotExist:
            return Response({'error': 'Primero genera el QR'}, status=400)

        if device.verify_token(code):
            device.confirmed = True
            device.save()
            return Response({'message': '2FA activado correctamente'})

        return Response({'error': 'Código incorrecto'}, status=400)
```

## URLs para 2FA

```python
# apps/authentication/urls.py
urlpatterns = [
    # ... endpoints existentes ...
    path('login/step1/', views.LoginStep1View.as_view(), name='login-step1'),
    path('login/step2/', views.LoginStep2TOTPView.as_view(), name='login-step2-totp'),
    path('2fa/setup/', views.Setup2FAView.as_view(), name='2fa-setup'),
]
```

## Códigos de respaldo (backup codes)

```python
class GenerateBackupCodesView(APIView):
    """Generar códigos de un solo uso para recuperación."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

        # Borrar códigos anteriores
        StaticDevice.objects.filter(user=request.user).delete()

        device = StaticDevice.objects.create(
            user=request.user,
            name='backup',
            confirmed=True
        )

        # Generar 10 códigos de respaldo
        codes = []
        for _ in range(10):
            token = StaticToken.random_token()
            StaticToken.objects.create(device=device, token=token)
            codes.append(token)

        return Response({
            'message': 'Guarda estos códigos en un lugar seguro. No se mostrarán de nuevo.',
            'codes': codes,
        })
```
