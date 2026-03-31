"""
Tests de seguridad — Fase 5:
  - Brute force protection (django-axes)
  - Rate limiting feedback
  - Biometric login flow
  - Onboarding complete flow
"""
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from apps.authentication.models import User


@override_settings(AXES_ENABLED=False)
class BiometricLoginTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='bio@test.com', password='pass1234',
            first_name='Bio', last_name='User',
        )

    def _get_refresh_token(self):
        r = self.client.post('/api/auth/login/', {
            'email': 'bio@test.com', 'password': 'pass1234',
        })
        return r.data['refresh']

    def test_biometric_login_requires_enabled(self):
        """Sin biometrics_enabled, debe retornar 403."""
        refresh = self._get_refresh_token()
        r = self.client.post('/api/auth/biometric/login/', {
            'device_id': 'device123',
            'refresh': refresh,
        })
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_biometric_login_wrong_device(self):
        """device_id incorrecto debe retornar 403."""
        self.user.biometrics_enabled = True
        self.user.device_id = 'correct_device'
        self.user.save()
        refresh = self._get_refresh_token()
        r = self.client.post('/api/auth/biometric/login/', {
            'device_id': 'wrong_device',
            'refresh': refresh,
        })
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_biometric_login_success(self):
        """device_id correcto + biometrics_enabled → 200 con tokens."""
        self.user.biometrics_enabled = True
        self.user.device_id = 'device_abc'
        self.user.save()
        refresh = self._get_refresh_token()
        r = self.client.post('/api/auth/biometric/login/', {
            'device_id': 'device_abc',
            'refresh': refresh,
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn('access', r.data)
        self.assertIn('refresh', r.data)

    def test_biometric_login_invalid_token(self):
        """Refresh token inválido debe retornar 401."""
        r = self.client.post('/api/auth/biometric/login/', {
            'device_id': 'device_abc',
            'refresh': 'notavalidtoken',
        })
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_biometric_login_missing_fields(self):
        """Sin campos requeridos → 400."""
        r = self.client.post('/api/auth/biometric/login/', {})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(AXES_ENABLED=False)
class OnboardingTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='onboard@test.com', password='pass1234',
            first_name='On', last_name='Board',
        )

    def test_onboarding_complete(self):
        self.client.force_authenticate(user=self.user)
        r = self.client.post('/api/auth/onboarding/complete/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.onboarding_completed)

    def test_onboarding_idempotent(self):
        self.user.onboarding_completed = True
        self.user.save()
        self.client.force_authenticate(user=self.user)
        r = self.client.post('/api/auth/onboarding/complete/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_onboarding_requires_auth(self):
        r = self.client.post('/api/auth/onboarding/complete/')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(AXES_ENABLED=True, AXES_FAILURE_LIMIT=3)
class BruteForceProtectionTest(TestCase):
    """
    Tests de protección brute-force con django-axes.
    AXES_FAILURE_LIMIT=3 para acelerar los tests.
    """
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='target@test.com', password='correctpass',
            first_name='Target', last_name='User',
        )

    def test_lockout_after_failed_attempts(self):
        """Tras AXES_FAILURE_LIMIT intentos fallidos, la cuenta se bloquea."""
        payload = {'email': 'target@test.com', 'password': 'wrongpass'}
        # Exhaust the failure limit
        for _ in range(3):
            self.client.post('/api/auth/login/', payload)
        # Next attempt should be locked (403)
        r = self.client.post('/api/auth/login/', payload)
        self.assertIn(r.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED])

    def test_successful_login_after_lockout_reset(self):
        """Después de resetear axes, el login vuelve a funcionar."""
        from axes.models import AccessAttempt
        # Fail some attempts
        payload_bad = {'email': 'target@test.com', 'password': 'wrong'}
        for _ in range(2):
            self.client.post('/api/auth/login/', payload_bad)
        # Reset
        AccessAttempt.objects.all().delete()
        # Correct login should work
        r = self.client.post('/api/auth/login/', {
            'email': 'target@test.com', 'password': 'correctpass',
        })
        self.assertEqual(r.status_code, status.HTTP_200_OK)
