from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.authentication.models import User


class LoginViewTest(APITestCase):
    """Tests para el endpoint de login /api/auth/login/"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
        )
        self.login_url = '/api/auth/login/'

    def test_login_success(self):
        """Credenciales válidas deben retornar 200 con access y refresh tokens."""
        payload = {
            'email': 'test@test.com',
            'password': 'testpass123',
        }
        response = self.client.post(self.login_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_wrong_password(self):
        """Contraseña incorrecta debe retornar 401."""
        payload = {
            'email': 'test@test.com',
            'password': 'wrongpassword',
        }
        response = self.client.post(self.login_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_wrong_email(self):
        """Email inexistente debe retornar 401 (sin enumerar usuarios)."""
        payload = {
            'email': 'noexiste@test.com',
            'password': 'testpass123',
        }
        response = self.client.post(self.login_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        # El mensaje de error debe ser idéntico al de contraseña incorrecta
        # para evitar enumeración de cuentas
        wrong_pass_response = self.client.post(
            self.login_url,
            {'email': 'test@test.com', 'password': 'wrongpassword'},
            format='json',
        )
        self.assertEqual(response.status_code, wrong_pass_response.status_code)

    def test_login_missing_fields(self):
        """Campos faltantes deben retornar 400."""
        # Sin contraseña
        response = self.client.post(
            self.login_url, {'email': 'test@test.com'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Sin email
        response = self.client.post(
            self.login_url, {'password': 'testpass123'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Body vacío
        response = self.client.post(self.login_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MeViewTest(APITestCase):
    """Tests para el endpoint /api/auth/me/"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
        )
        self.me_url = '/api/auth/me/'
        self.login_url = '/api/auth/login/'

    def _get_access_token(self):
        """Helper: obtiene un access token para el usuario de prueba."""
        response = self.client.post(
            self.login_url,
            {'email': 'test@test.com', 'password': 'testpass123'},
            format='json',
        )
        return response.data['access']

    def test_me_authenticated(self):
        """Con token válido debe retornar 200 y datos del usuario."""
        token = self._get_access_token()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@test.com')
        self.assertEqual(response.data['first_name'], 'Test')
        self.assertEqual(response.data['last_name'], 'User')

    def test_me_unauthenticated(self):
        """Sin token debe retornar 401."""
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LogoutViewTest(APITestCase):
    """Tests para el endpoint /api/auth/logout/"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
        )
        self.login_url = '/api/auth/login/'
        self.logout_url = '/api/auth/logout/'

    def _get_tokens(self):
        """Helper: obtiene access y refresh tokens para el usuario de prueba."""
        response = self.client.post(
            self.login_url,
            {'email': 'test@test.com', 'password': 'testpass123'},
            format='json',
        )
        return response.data['access'], response.data['refresh']

    def test_logout_success(self):
        """Con refresh token válido debe retornar 200 o 204."""
        access, refresh = self._get_tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        response = self.client.post(
            self.logout_url, {'refresh': refresh}, format='json'
        )

        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT],
        )

    def test_logout_invalid_token(self):
        """Token de refresh inválido debe retornar 400."""
        access, _ = self._get_tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        response = self.client.post(
            self.logout_url, {'refresh': 'token-invalido-xxx'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RefreshViewTest(APITestCase):
    """Tests para el endpoint /api/auth/refresh/"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
        )
        self.login_url = '/api/auth/login/'
        self.refresh_url = '/api/auth/refresh/'

    def _get_refresh_token(self):
        """Helper: obtiene el refresh token para el usuario de prueba."""
        response = self.client.post(
            self.login_url,
            {'email': 'test@test.com', 'password': 'testpass123'},
            format='json',
        )
        return response.data['refresh']

    def test_refresh_success(self):
        """Refresh token válido debe retornar 200 con nuevo access token."""
        refresh = self._get_refresh_token()

        response = self.client.post(
            self.refresh_url, {'refresh': refresh}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_refresh_invalid(self):
        """Refresh token inválido debe retornar 401."""
        response = self.client.post(
            self.refresh_url,
            {'refresh': 'token-invalido-xxx'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
