from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from .serializers import (
    LoginSerializer,
    UserSerializer,
    BiometricEnableSerializer,
    ChangePasswordSerializer,
)


@method_decorator(ratelimit(key='ip', rate='5/m', block=False), name='dispatch')
class LoginView(APIView):
    """
    POST /api/auth/login/
    Rate limited: 5 intentos/min por IP.
    """
    permission_classes = []

    def post(self, request):
        if getattr(request, 'limited', False):
            return Response(
                {'detail': 'Demasiados intentos de login. Intenta de nuevo en un minuto.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        serializer = LoginSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(
                {'detail': 'Credenciales inválidas.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        return Response({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'user':    UserSerializer(user).data,
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """POST /api/auth/logout/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response(
                    {'detail': 'Se requiere el campo "refresh".'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {'detail': 'Sesión cerrada correctamente.'},
                status=status.HTTP_200_OK,
            )
        except TokenError:
            return Response(
                {'detail': 'Token inválido o ya expirado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )


@method_decorator(ratelimit(key='ip', rate='20/m', block=False), name='dispatch')
class RefreshView(TokenRefreshView):
    """POST /api/auth/refresh/ — Rate limited: 20/min por IP."""

    def post(self, request, *args, **kwargs):
        if getattr(request, 'limited', False):
            return Response(
                {'detail': 'Demasiadas solicitudes de refresh. Intenta más tarde.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        return super().post(request, *args, **kwargs)


class MeView(APIView):
    """GET /api/auth/me/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)


class BiometricEnableView(APIView):
    """POST /api/auth/biometric/enable/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BiometricEnableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.biometrics_enabled = True
        user.device_id = serializer.validated_data['device_id']
        user.save(update_fields=['biometrics_enabled', 'device_id'])

        return Response({
            'detail': 'Autenticación biométrica activada.',
            'biometrics_enabled': True,
            'device_id': user.device_id,
        }, status=status.HTTP_200_OK)


class BiometricDisableView(APIView):
    """POST /api/auth/biometric/disable/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        user.biometrics_enabled = False
        user.device_id = None
        user.save(update_fields=['biometrics_enabled', 'device_id'])

        return Response(
            {'detail': 'Autenticación biométrica desactivada.'},
            status=status.HTTP_200_OK,
        )


class BiometricLoginView(APIView):
    """
    POST /api/auth/biometric/login/

    Fase 6: login sin contraseña usando device_id verificado en el cliente.
    El cliente envía:
      - device_id: el ID del dispositivo registrado
      - refresh: un refresh token válido previamente obtenido

    El servidor:
      1. Valida el refresh token
      2. Obtiene el usuario del token
      3. Verifica que biometrics_enabled=True y que device_id coincide
      4. Emite un nuevo access token (rotando el refresh)
    """
    permission_classes = [AllowAny]

    def post(self, request):
        device_id     = request.data.get('device_id', '').strip()
        refresh_token = request.data.get('refresh', '').strip()

        if not device_id or not refresh_token:
            return Response(
                {'detail': 'Se requieren device_id y refresh.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate the refresh token and get the user
        try:
            token = RefreshToken(refresh_token)
            user_id = token.payload.get('user_id')
        except TokenError:
            return Response(
                {'detail': 'Token inválido o expirado.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Fetch the user
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {'detail': 'Usuario no encontrado.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Verify biometric is enabled and device_id matches
        if not user.biometrics_enabled:
            return Response(
                {'detail': 'La autenticación biométrica no está activada para este usuario.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if user.device_id != device_id:
            return Response(
                {'detail': 'El device_id no coincide con el registrado.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not user.is_active:
            return Response(
                {'detail': 'La cuenta está desactivada.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Blacklist old token and issue new pair (rotation)
        try:
            token.blacklist()
        except Exception:
            pass  # token_blacklist may not be enabled, proceed anyway

        new_refresh = RefreshToken.for_user(user)
        return Response({
            'access':  str(new_refresh.access_token),
            'refresh': str(new_refresh),
            'user':    UserSerializer(user).data,
        }, status=status.HTTP_200_OK)


class OnboardingCompleteView(APIView):
    """
    POST /api/auth/onboarding/complete/
    Fase 6: marca al usuario como onboarded.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.onboarding_completed:
            return Response(
                {'detail': 'El onboarding ya estaba completado.'},
                status=status.HTTP_200_OK,
            )
        user.onboarding_completed = True
        user.save(update_fields=['onboarding_completed'])
        return Response({
            'detail': 'Onboarding completado.',
            'user': UserSerializer(user).data,
        }, status=status.HTTP_200_OK)
