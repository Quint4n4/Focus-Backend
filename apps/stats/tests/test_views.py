from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.areas.models import Area
from apps.activities.models import Activity

User = get_user_model()


class PersonalStatsViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.area = Area.objects.create(name='Dev')
        self.worker = User.objects.create_user(
            email='worker@test.com', password='pass1234',
            first_name='Worker', last_name='One', role='trabajador', area=self.area,
        )
        self.worker2 = User.objects.create_user(
            email='worker2@test.com', password='pass1234',
            first_name='Worker', last_name='Two', role='trabajador', area=self.area,
        )

    def _make_activity(self, owner=None, **kwargs):
        return Activity.objects.create(
            title=kwargs.get('title', 'Task'),
            area=self.area,
            owner=owner or self.worker,
            status=kwargs.get('status', 'inbox'),
        )

    def test_unauthenticated_returns_401(self):
        r = self.client.get('/api/stats/personal/')
        self.assertEqual(r.status_code, 401)

    def test_empty_stats_returns_zeros(self):
        self.client.force_authenticate(user=self.worker)
        r = self.client.get('/api/stats/personal/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['total_owned'], 0)
        self.assertEqual(r.data['total_assigned'], 0)
        # all status keys present
        for key in ['inbox', 'today', 'tomorrow', 'scheduled', 'pending', 'completed']:
            self.assertIn(key, r.data['by_status'])
            self.assertEqual(r.data['by_status'][key], 0)

    def test_by_status_counts_correctly(self):
        self._make_activity(status='inbox')
        self._make_activity(status='inbox')
        self._make_activity(status='today')
        self.client.force_authenticate(user=self.worker)
        r = self.client.get('/api/stats/personal/')
        self.assertEqual(r.data['by_status']['inbox'], 2)
        self.assertEqual(r.data['by_status']['today'], 1)

    def test_completed_today(self):
        act = self._make_activity(status='completed')
        act.completed_at = timezone.now()
        act.save()
        self.client.force_authenticate(user=self.worker)
        r = self.client.get('/api/stats/personal/')
        self.assertEqual(r.data['completed_today'], 1)

    def test_total_owned_and_assigned(self):
        self._make_activity()
        assigned = self._make_activity(owner=self.worker2)
        assigned.assigned_to = self.worker
        assigned.save()
        self.client.force_authenticate(user=self.worker)
        r = self.client.get('/api/stats/personal/')
        self.assertEqual(r.data['total_owned'], 1)
        self.assertEqual(r.data['total_assigned'], 1)

    def test_other_user_activities_not_counted(self):
        self._make_activity(owner=self.worker2)
        self.client.force_authenticate(user=self.worker)
        r = self.client.get('/api/stats/personal/')
        self.assertEqual(r.data['total_owned'], 0)


class AreaStatsViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.area  = Area.objects.create(name='Dev')
        self.area2 = Area.objects.create(name='Ops')
        self.super_admin = User.objects.create_user(
            email='super@test.com', password='pass1234',
            first_name='Super', last_name='Admin', role='super_admin',
        )
        self.admin = User.objects.create_user(
            email='admin@test.com', password='pass1234',
            first_name='Admin', last_name='User', role='admin_area', area=self.area,
        )
        self.worker = User.objects.create_user(
            email='worker@test.com', password='pass1234',
            first_name='Worker', last_name='One', role='trabajador', area=self.area,
        )

    def test_worker_cannot_access_area_stats(self):
        self.client.force_authenticate(user=self.worker)
        r = self.client.get(f'/api/stats/area/{self.area.id}/')
        self.assertEqual(r.status_code, 403)

    def test_admin_can_access_own_area(self):
        self.client.force_authenticate(user=self.admin)
        r = self.client.get(f'/api/stats/area/{self.area.id}/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['area_id'], str(self.area.id))

    def test_admin_cannot_access_other_area(self):
        self.client.force_authenticate(user=self.admin)
        r = self.client.get(f'/api/stats/area/{self.area2.id}/')
        self.assertEqual(r.status_code, 403)

    def test_super_admin_can_access_any_area(self):
        self.client.force_authenticate(user=self.super_admin)
        r = self.client.get(f'/api/stats/area/{self.area2.id}/')
        self.assertEqual(r.status_code, 200)

    def test_completion_rate_calculation(self):
        for i in range(5):
            Activity.objects.create(
                title=f'Task {i}', area=self.area, owner=self.worker, status='completed',
            )
        for i in range(5):
            Activity.objects.create(
                title=f'Task {i+5}', area=self.area, owner=self.worker, status='inbox',
            )
        self.client.force_authenticate(user=self.admin)
        r = self.client.get(f'/api/stats/area/{self.area.id}/')
        self.assertEqual(r.data['total_activities'], 10)
        self.assertEqual(r.data['completed_activities'], 5)
        self.assertEqual(r.data['completion_rate'], 50.0)

    def test_members_list_present(self):
        self.client.force_authenticate(user=self.admin)
        r = self.client.get(f'/api/stats/area/{self.area.id}/')
        self.assertIn('members', r.data)
        self.assertIsInstance(r.data['members'], list)


class DrilldownViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.area  = Area.objects.create(name='Dev')
        self.area2 = Area.objects.create(name='Ops')
        self.super_admin = User.objects.create_user(
            email='super@test.com', password='pass1234',
            first_name='Super', last_name='Admin', role='super_admin',
        )
        self.admin = User.objects.create_user(
            email='admin@test.com', password='pass1234',
            first_name='Admin', last_name='User', role='admin_area', area=self.area,
        )
        self.worker = User.objects.create_user(
            email='worker@test.com', password='pass1234',
            first_name='Worker', last_name='One', role='trabajador', area=self.area,
        )

    def test_worker_cannot_access_drilldown(self):
        self.client.force_authenticate(user=self.worker)
        r = self.client.get('/api/stats/drilldown/')
        self.assertEqual(r.status_code, 403)

    def test_admin_forced_to_own_area(self):
        # Create activities in both areas
        Activity.objects.create(title='Dev Task', area=self.area, owner=self.worker, status='inbox')
        Activity.objects.create(title='Ops Task', area=self.area2, owner=self.worker, status='inbox')
        self.client.force_authenticate(user=self.admin)
        # Even if we pass area2, admin is forced to their own area
        r = self.client.get(f'/api/stats/drilldown/?area={self.area2.id}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['summary']['total'], 1)  # only dev area

    def test_super_admin_all_areas(self):
        Activity.objects.create(title='Dev', area=self.area, owner=self.worker, status='inbox')
        Activity.objects.create(title='Ops', area=self.area2, owner=self.worker, status='inbox')
        self.client.force_authenticate(user=self.super_admin)
        r = self.client.get('/api/stats/drilldown/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['summary']['total'], 2)

    def test_by_user_aggregation(self):
        Activity.objects.create(title='T1', area=self.area, owner=self.worker, status='inbox')
        Activity.objects.create(title='T2', area=self.area, owner=self.worker, status='completed')
        self.client.force_authenticate(user=self.admin)
        r = self.client.get('/api/stats/drilldown/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['by_user']), 1)
        self.assertEqual(r.data['by_user'][0]['total'], 2)
        self.assertEqual(r.data['by_user'][0]['completed'], 1)

    def test_all_status_keys_present(self):
        self.client.force_authenticate(user=self.admin)
        r = self.client.get('/api/stats/drilldown/')
        for key in ['inbox', 'today', 'tomorrow', 'scheduled', 'pending', 'completed']:
            self.assertIn(key, r.data['by_status'])
