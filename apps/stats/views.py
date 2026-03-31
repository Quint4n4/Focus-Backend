from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.activities.models import Activity
from apps.areas.models import Area
from core.permissions import IsAdminAreaOrAbove, IsWorkerOrAbove

User = get_user_model()


class PersonalStatsView(APIView):
    permission_classes = [IsWorkerOrAbove]

    def get(self, request):
        user = request.user
        now = timezone.now()
        today = now.date()
        week_start = today - timedelta(days=today.weekday())  # Monday

        owned_qs = Activity.objects.filter(owner=user)

        # Status distribution — single query, ensure all 6 statuses present
        status_counts = owned_qs.values('status').annotate(count=Count('id'))
        by_status = {item['status']: item['count'] for item in status_counts}
        for choice_val, _ in Activity.Status.choices:
            by_status.setdefault(choice_val, 0)

        completed_today = Activity.objects.filter(
            owner=user, status='completed', completed_at__date=today,
        ).count()

        completed_this_week = Activity.objects.filter(
            owner=user, status='completed', completed_at__date__gte=week_start,
        ).count()

        completed_this_month = Activity.objects.filter(
            owner=user, status='completed',
            completed_at__year=now.year,
            completed_at__month=now.month,
        ).count()

        return Response({
            'by_status': by_status,
            'completed_today': completed_today,
            'completed_this_week': completed_this_week,
            'completed_this_month': completed_this_month,
            'total_owned': owned_qs.count(),
            'total_assigned': Activity.objects.filter(assigned_to=user).count(),
        })


class AreaStatsView(APIView):
    permission_classes = [IsAdminAreaOrAbove]

    def get(self, request, area_pk):
        area = get_object_or_404(Area, pk=area_pk)

        # admin_area can only see their own area
        if request.user.role == 'admin_area':
            if str(request.user.area_id) != str(area_pk):
                raise PermissionDenied('Solo puedes ver estadísticas de tu propia área.')

        qs = Activity.objects.filter(area=area)
        total = qs.count()
        completed = qs.filter(status='completed').count()
        completion_rate = round(completed / total * 100, 1) if total > 0 else 0.0

        # Status distribution
        status_counts = qs.values('status').annotate(c=Count('id'))
        by_status = {item['status']: item['c'] for item in status_counts}
        for choice_val, _ in Activity.Status.choices:
            by_status.setdefault(choice_val, 0)

        # Per-member aggregation — single query using annotate
        members_qs = User.objects.filter(area=area).annotate(
            owned_count=Count(
                'owned_activities',
                filter=Q(owned_activities__area=area),
            ),
            assigned_count=Count(
                'assigned_activities',
                filter=Q(assigned_activities__area=area),
            ),
            completed_count=Count(
                'owned_activities',
                filter=Q(owned_activities__area=area, owned_activities__status='completed'),
            ),
        )

        members = [
            {
                'user_id':   str(m.id),
                'email':     m.email,
                'full_name': m.full_name,
                'owned':     m.owned_count,
                'assigned':  m.assigned_count,
                'completed': m.completed_count,
            }
            for m in members_qs
        ]

        return Response({
            'area_id':              str(area.id),
            'area_name':            area.name,
            'total_activities':     total,
            'completed_activities': completed,
            'completion_rate':      completion_rate,
            'by_status':            by_status,
            'members':              members,
        })


class DrilldownView(APIView):
    permission_classes = [IsAdminAreaOrAbove]

    def get(self, request):
        params = request.query_params
        user = request.user
        qs = Activity.objects.all()
        filters_used = {}

        # Area filter — admin_area is always forced to their own area
        if user.role == 'admin_area':
            qs = qs.filter(area=user.area)
            filters_used['area'] = str(user.area_id)
        elif params.get('area'):
            qs = qs.filter(area_id=params['area'])
            filters_used['area'] = params['area']

        # Project filter
        if params.get('project'):
            qs = qs.filter(project_id=params['project'])
            filters_used['project'] = params['project']

        # User filter (owner)
        if params.get('user'):
            qs = qs.filter(owner_id=params['user'])
            filters_used['user'] = params['user']

        # Date range on created_at
        if params.get('from'):
            qs = qs.filter(created_at__date__gte=params['from'])
            filters_used['from'] = params['from']
        if params.get('to'):
            qs = qs.filter(created_at__date__lte=params['to'])
            filters_used['to'] = params['to']

        total = qs.count()
        completed = qs.filter(status='completed').count()
        completion_rate = round(completed / total * 100, 1) if total > 0 else 0.0

        # Status breakdown
        status_counts = qs.values('status').annotate(c=Count('id'))
        by_status = {item['status']: item['c'] for item in status_counts}
        for choice_val, _ in Activity.Status.choices:
            by_status.setdefault(choice_val, 0)

        # By project (group by project_id + project name)
        by_project_raw = (
            qs.values('project_id', 'project__name')
              .annotate(total=Count('id'), completed=Count('id', filter=Q(status='completed')))
              .order_by('-total')
        )
        by_project = [
            {
                'project_id': str(r['project_id']) if r['project_id'] else None,
                'name':       r['project__name'] or '(Sin proyecto)',
                'total':      r['total'],
                'completed':  r['completed'],
            }
            for r in by_project_raw
        ]

        # By user (group by owner)
        by_user_raw = (
            qs.values('owner_id', 'owner__email')
              .annotate(total=Count('id'), completed=Count('id', filter=Q(status='completed')))
              .order_by('-total')
        )
        by_user = [
            {
                'user_id':   str(r['owner_id']),
                'email':     r['owner__email'],
                'total':     r['total'],
                'completed': r['completed'],
            }
            for r in by_user_raw
        ]

        return Response({
            'filters': filters_used,
            'summary': {
                'total':           total,
                'completed':       completed,
                'completion_rate': completion_rate,
            },
            'by_status':  by_status,
            'by_project': by_project,
            'by_user':    by_user,
        })
