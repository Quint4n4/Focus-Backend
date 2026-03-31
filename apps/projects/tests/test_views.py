from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.areas.models import Area
from apps.projects.models import Project
from apps.activities.models import Activity

User = get_user_model()


class ProjectViewTest(TestCase):
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
        self.worker2 = User.objects.create_user(
            email='worker2@test.com', password='pass1234',
            first_name='Worker', last_name='Two', role='trabajador', area=self.area2,
        )

    def _make_project(self, area=None, **kwargs):
        return Project.objects.create(
            name=kwargs.get('name', 'Test Project'),
            area=area or self.area,
            created_by=kwargs.get('created_by', self.admin),
            status=kwargs.get('status', 'active'),
        )

    def test_admin_can_create_project(self):
        self.client.force_authenticate(user=self.admin)
        r = self.client.post('/api/projects/', {'name': 'Sprint 1', 'area': str(self.area.id)})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data['name'], 'Sprint 1')

    def test_worker_cannot_create_project(self):
        self.client.force_authenticate(user=self.worker)
        r = self.client.post('/api/projects/', {'name': 'Sprint X', 'area': str(self.area.id)})
        self.assertEqual(r.status_code, 403)

    def test_admin_area_cannot_create_in_other_area(self):
        self.client.force_authenticate(user=self.admin)
        r = self.client.post('/api/projects/', {'name': 'Ops Sprint', 'area': str(self.area2.id)})
        self.assertEqual(r.status_code, 403)

    def test_worker_sees_only_own_area_projects(self):
        self._make_project(area=self.area, name='Dev Project')
        self._make_project(area=self.area2, name='Ops Project')
        self.client.force_authenticate(user=self.worker)
        r = self.client.get('/api/projects/')
        self.assertEqual(r.status_code, 200)
        names = [p['name'] for p in r.data['results']]
        self.assertIn('Dev Project', names)
        self.assertNotIn('Ops Project', names)

    def test_super_admin_sees_all_projects(self):
        self._make_project(area=self.area, name='Dev Project')
        self._make_project(area=self.area2, name='Ops Project')
        self.client.force_authenticate(user=self.super_admin)
        r = self.client.get('/api/projects/')
        self.assertEqual(r.status_code, 200)
        names = [p['name'] for p in r.data['results']]
        self.assertIn('Dev Project', names)
        self.assertIn('Ops Project', names)

    def test_get_project_detail(self):
        project = self._make_project()
        self.client.force_authenticate(user=self.worker)
        r = self.client.get(f'/api/projects/{project.id}/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['name'], project.name)

    def test_worker_cannot_access_other_area_project(self):
        project = self._make_project(area=self.area2)
        self.client.force_authenticate(user=self.worker)
        r = self.client.get(f'/api/projects/{project.id}/')
        self.assertEqual(r.status_code, 404)

    def test_admin_can_patch_project(self):
        project = self._make_project()
        self.client.force_authenticate(user=self.admin)
        r = self.client.patch(f'/api/projects/{project.id}/', {'name': 'Updated'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['name'], 'Updated')

    def test_worker_cannot_patch_project(self):
        project = self._make_project()
        self.client.force_authenticate(user=self.worker)
        r = self.client.patch(f'/api/projects/{project.id}/', {'name': 'Hacked'})
        self.assertEqual(r.status_code, 403)

    def test_admin_can_delete_project(self):
        project = self._make_project()
        self.client.force_authenticate(user=self.admin)
        r = self.client.delete(f'/api/projects/{project.id}/')
        self.assertEqual(r.status_code, 204)
        self.assertFalse(Project.objects.filter(id=project.id).exists())

    def test_project_activities_list(self):
        project = self._make_project()
        Activity.objects.create(
            title='Task 1', area=self.area, owner=self.worker,
            project=project, status='inbox',
        )
        self.client.force_authenticate(user=self.worker)
        r = self.client.get(f'/api/projects/{project.id}/activities/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)

    def test_project_progress_empty(self):
        project = self._make_project()
        self.client.force_authenticate(user=self.worker)
        r = self.client.get(f'/api/projects/{project.id}/progress/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['total'], 0)
        self.assertEqual(r.data['completion_percentage'], 0.0)

    def test_project_progress_with_activities(self):
        project = self._make_project()
        Activity.objects.create(title='T1', area=self.area, owner=self.worker,
                                project=project, status='completed')
        Activity.objects.create(title='T2', area=self.area, owner=self.worker,
                                project=project, status='inbox')
        self.client.force_authenticate(user=self.worker)
        r = self.client.get(f'/api/projects/{project.id}/progress/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['total'], 2)
        self.assertEqual(r.data['completed'], 1)
        self.assertEqual(r.data['completion_percentage'], 50.0)

    def test_unauthenticated_cannot_access(self):
        r = self.client.get('/api/projects/')
        self.assertEqual(r.status_code, 401)
