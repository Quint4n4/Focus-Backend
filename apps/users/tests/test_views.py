from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.areas.models import Area
from apps.users.models import Invitation

User = get_user_model()


def make_area(name='Test Area'):
    return Area.objects.create(name=name)


def make_user(email, password='testpass123', role='trabajador', area=None, **kwargs):
    return User.objects.create_user(
        email=email,
        password=password,
        first_name=kwargs.get('first_name', 'Test'),
        last_name=kwargs.get('last_name', 'User'),
        role=role,
        area=area,
    )


class InviteViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.area   = make_area()

    def test_admin_can_invite(self):
        admin = make_user('admin@example.com', role='admin_area', area=self.area)
        self.client.force_authenticate(user=admin)

        response = self.client.post('/api/users/invite/', {
            'area': str(self.area.id),
            'role': 'trabajador',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertIn('token', data)
        self.assertIn('expires_at', data)
        self.assertEqual(data['role'], 'trabajador')

    def test_super_admin_can_invite_any_area(self):
        super_admin = make_user('super@example.com', role='super_admin')
        other_area  = make_area('Other Area')
        self.client.force_authenticate(user=super_admin)

        response = self.client.post('/api/users/invite/', {
            'area': str(other_area.id),
            'role': 'admin_area',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_worker_cannot_invite(self):
        worker = make_user('worker@example.com', role='trabajador', area=self.area)
        self.client.force_authenticate(user=worker)

        response = self.client.post('/api/users/invite/', {
            'area': str(self.area.id),
            'role': 'trabajador',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_area_cannot_invite_to_other_area(self):
        admin      = make_user('admin@example.com', role='admin_area', area=self.area)
        other_area = make_area('Other Area')
        self.client.force_authenticate(user=admin)

        response = self.client.post('/api/users/invite/', {
            'area': str(other_area.id),
            'role': 'trabajador',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AcceptInviteViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.area   = make_area()
        self.admin  = make_user('admin@example.com', role='admin_area', area=self.area)

    def _create_invitation(self, hours_offset=24, used=False):
        raw_token, token_hash = Invitation.generate_token()
        invitation = Invitation.objects.create(
            token_hash=token_hash,
            area=self.area,
            role='trabajador',
            created_by=self.admin,
            expires_at=timezone.now() + timedelta(hours=hours_offset),
            used=used,
        )
        return raw_token, invitation

    def test_accept_invite_creates_user(self):
        raw_token, _ = self._create_invitation()

        response = self.client.post('/api/users/accept-invite/', {
            'token':      raw_token,
            'email':      'newuser@example.com',
            'first_name': 'New',
            'last_name':  'User',
            'password':   'securepass123',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data['email'], 'newuser@example.com')
        self.assertEqual(data['role'], 'trabajador')
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())

    def test_accept_invite_marks_invitation_used(self):
        raw_token, invitation = self._create_invitation()

        self.client.post('/api/users/accept-invite/', {
            'token':      raw_token,
            'email':      'newuser2@example.com',
            'first_name': 'New',
            'last_name':  'User',
            'password':   'securepass123',
        }, format='json')

        invitation.refresh_from_db()
        self.assertTrue(invitation.used)

    def test_accept_invite_expired_token(self):
        raw_token, _ = self._create_invitation(hours_offset=-1)  # already expired

        response = self.client.post('/api/users/accept-invite/', {
            'token':      raw_token,
            'email':      'expired@example.com',
            'first_name': 'Exp',
            'last_name':  'User',
            'password':   'securepass123',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accept_invite_used_token(self):
        raw_token, _ = self._create_invitation(used=True)

        response = self.client.post('/api/users/accept-invite/', {
            'token':      raw_token,
            'email':      'used@example.com',
            'first_name': 'Used',
            'last_name':  'User',
            'password':   'securepass123',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accept_invite_invalid_token(self):
        response = self.client.post('/api/users/accept-invite/', {
            'token':      'totally-invalid-token',
            'email':      'bad@example.com',
            'first_name': 'Bad',
            'last_name':  'Token',
            'password':   'securepass123',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserListViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.area   = make_area()

    def test_user_list_admin_only(self):
        worker = make_user('worker@example.com', role='trabajador', area=self.area)
        self.client.force_authenticate(user=worker)

        response = self.client.get('/api/users/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_own_area_users(self):
        admin  = make_user('admin@example.com',  role='admin_area', area=self.area)
        worker = make_user('worker@example.com', role='trabajador', area=self.area)
        self.client.force_authenticate(user=admin)

        response = self.client.get('/api/users/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = [u['email'] for u in response.json()]
        self.assertIn('worker@example.com', emails)

    def test_super_admin_sees_all_users(self):
        other_area = make_area('Other')
        super_admin = make_user('super@example.com', role='super_admin')
        make_user('user1@example.com', area=self.area)
        make_user('user2@example.com', area=other_area)
        self.client.force_authenticate(user=super_admin)

        response = self.client.get('/api/users/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.json()), 3)

    def test_unauthenticated_cannot_list(self):
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserDetailViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.area   = make_area()

    def test_worker_can_get_own_detail(self):
        worker = make_user('worker@example.com', role='trabajador', area=self.area)
        self.client.force_authenticate(user=worker)

        response = self.client.get(f'/api/users/{worker.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['email'], 'worker@example.com')

    def test_worker_cannot_see_other_user(self):
        worker  = make_user('worker@example.com',  role='trabajador', area=self.area)
        other   = make_user('other@example.com',   role='trabajador', area=self.area)
        self.client.force_authenticate(user=worker)

        response = self.client.get(f'/api/users/{other.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_worker_can_patch_own_name(self):
        worker = make_user('worker@example.com', role='trabajador', area=self.area)
        self.client.force_authenticate(user=worker)

        response = self.client.patch(f'/api/users/{worker.id}/', {
            'first_name': 'Updated',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['first_name'], 'Updated')

    def test_super_admin_can_see_any_user(self):
        super_admin = make_user('super@example.com', role='super_admin')
        worker      = make_user('worker@example.com', role='trabajador', area=self.area)
        self.client.force_authenticate(user=super_admin)

        response = self.client.get(f'/api/users/{worker.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
