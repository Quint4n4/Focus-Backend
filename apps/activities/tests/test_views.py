from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from apps.areas.models import Area
from apps.activities.models import Activity, ActivityLog

User = get_user_model()

ACTIVITIES_URL = '/api/activities/'


def activity_url(pk):
    return f'/api/activities/{pk}/'


def move_url(pk):
    return f'/api/activities/{pk}/move/'


def complete_url(pk):
    return f'/api/activities/{pk}/complete/'


def assign_url(pk):
    return f'/api/activities/{pk}/assign/'


def logs_url(pk):
    return f'/api/activities/{pk}/logs/'


class ActivityViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.area = Area.objects.create(name='Dev')
        self.area2 = Area.objects.create(name='Ops')

        self.super_admin = User.objects.create_user(
            email='super@test.com',
            password='pass1234',
            first_name='Super',
            last_name='Admin',
            role='super_admin',
        )
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='pass1234',
            first_name='Admin',
            last_name='User',
            role='admin_area',
            area=self.area,
        )
        self.worker = User.objects.create_user(
            email='worker@test.com',
            password='pass1234',
            first_name='Worker',
            last_name='One',
            role='trabajador',
            area=self.area,
        )
        self.worker2 = User.objects.create_user(
            email='worker2@test.com',
            password='pass1234',
            first_name='Worker',
            last_name='Two',
            role='trabajador',
            area=self.area2,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_activity(self, owner=None, area=None, **kwargs):
        owner = owner or self.worker
        area = area or self.area
        return Activity.objects.create(
            title='Test Activity',
            owner=owner,
            area=area,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_worker_can_create_activity(self):
        self.client.force_authenticate(user=self.worker)
        payload = {
            'title': 'Nueva tarea',
            'description': 'Descripción de prueba',
            'area': str(self.area.id),
        }
        response = self.client.post(ACTIVITIES_URL, payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['title'], 'Nueva tarea')

    def test_worker_sees_only_own_activities(self):
        # Activity owned by worker
        own = self._make_activity(owner=self.worker)
        # Activity assigned to worker (owned by admin)
        assigned = self._make_activity(owner=self.admin, assigned_to=self.worker)
        # Activity belonging to same area but neither owned nor assigned to worker
        other = self._make_activity(owner=self.admin)

        self.client.force_authenticate(user=self.worker)
        response = self.client.get(ACTIVITIES_URL)
        self.assertEqual(response.status_code, 200)

        ids = [str(item['id']) for item in response.data]
        self.assertIn(str(own.id), ids)
        self.assertIn(str(assigned.id), ids)
        self.assertNotIn(str(other.id), ids)

    def test_admin_sees_area_activities(self):
        area_activity = self._make_activity(owner=self.worker, area=self.area)
        other_area_activity = self._make_activity(owner=self.worker2, area=self.area2)

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(ACTIVITIES_URL)
        self.assertEqual(response.status_code, 200)

        ids = [str(item['id']) for item in response.data]
        self.assertIn(str(area_activity.id), ids)
        self.assertNotIn(str(other_area_activity.id), ids)

    def test_super_admin_sees_all(self):
        a1 = self._make_activity(owner=self.worker, area=self.area)
        a2 = self._make_activity(owner=self.worker2, area=self.area2)

        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get(ACTIVITIES_URL)
        self.assertEqual(response.status_code, 200)

        ids = [str(item['id']) for item in response.data]
        self.assertIn(str(a1.id), ids)
        self.assertIn(str(a2.id), ids)

    def test_move_activity_status(self):
        activity = self._make_activity(owner=self.worker)
        self.assertEqual(activity.status, 'inbox')

        self.client.force_authenticate(user=self.worker)
        response = self.client.patch(move_url(activity.id), {'status': 'today'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'today')

        activity.refresh_from_db()
        self.assertEqual(activity.status, 'today')

    def test_complete_activity(self):
        activity = self._make_activity(owner=self.worker)

        self.client.force_authenticate(user=self.worker)
        response = self.client.post(complete_url(activity.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'completed')
        self.assertIsNotNone(response.data['completed_at'])

        activity.refresh_from_db()
        self.assertEqual(activity.status, 'completed')
        self.assertIsNotNone(activity.completed_at)

    def test_complete_already_completed_returns_400(self):
        activity = self._make_activity(owner=self.worker, status='completed')

        self.client.force_authenticate(user=self.worker)
        response = self.client.post(complete_url(activity.id))
        self.assertEqual(response.status_code, 400)
        self.assertIn('detail', response.data)

    def test_assign_requires_admin(self):
        activity = self._make_activity(owner=self.worker)

        self.client.force_authenticate(user=self.worker)
        response = self.client.patch(
            assign_url(activity.id),
            {'assigned_to': str(self.worker.id)},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_assign_activity(self):
        activity = self._make_activity(owner=self.worker)

        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            assign_url(activity.id),
            {'assigned_to': str(self.worker.id)},
            format='json',
        )
        self.assertEqual(response.status_code, 200)

        activity.refresh_from_db()
        self.assertEqual(activity.assigned_to_id, self.worker.pk)
        self.assertEqual(activity.assigned_by_id, self.admin.pk)

    def test_log_created_on_activity_create(self):
        self.client.force_authenticate(user=self.worker)
        payload = {
            'title': 'Log test activity',
            'area': str(self.area.id),
        }
        response = self.client.post(ACTIVITIES_URL, payload, format='json')
        self.assertEqual(response.status_code, 201)

        activity_id = response.data['id']
        logs_response = self.client.get(logs_url(activity_id))
        self.assertEqual(logs_response.status_code, 200)

        # At least one log should exist with event_type='created'
        event_types = [log['event_type'] for log in logs_response.data]
        self.assertIn('created', event_types)

    def test_worker_cannot_access_other_area_activity(self):
        # Activity owned by worker2 in area2
        activity = self._make_activity(owner=self.worker2, area=self.area2)

        self.client.force_authenticate(user=self.worker)
        response = self.client.get(activity_url(activity.id))
        self.assertEqual(response.status_code, 404)
