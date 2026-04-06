from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, FloatField, Q
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.activities.models import Activity
from apps.areas.models import Area
from core.permissions import IsAdminAreaOrAbove, IsSuperAdmin, IsWorkerOrAbove

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
            qs = qs.filter(area_id=user.area_id)
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


class GlobalStatsView(APIView):
    """
    GET /api/stats/global/
    Solo Super Admin. Devuelve un resumen por cada área con su tasa de completado
    y lista de AA — equivale al bloque "Rendimiento por equipos" que ve el SA en Flutter.
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        areas = Area.objects.all()
        result = []
        for area in areas:
            qs = Activity.objects.filter(area=area)
            total     = qs.count()
            completed = qs.filter(status='completed').count()
            rate      = round(completed / total * 100, 1) if total > 0 else 0.0

            # Admin(s) del área
            admins = User.objects.filter(area=area, role='admin_area').values(
                'id', 'email', 'first_name', 'last_name'
            )
            admin_list = [
                {
                    'id':         str(a['id']),
                    'email':      a['email'],
                    'full_name':  f"{a['first_name']} {a['last_name']}".strip(),
                }
                for a in admins
            ]

            result.append({
                'area_id':         str(area.id),
                'area_name':       area.name,
                'total_activities': total,
                'completed':       completed,
                'completion_rate': rate,
                'admins':          admin_list,
            })

        # Ordenar por completion_rate descendente
        result.sort(key=lambda x: x['completion_rate'], reverse=True)
        return Response(result)


class WorkerStatsView(APIView):
    """
    GET /api/stats/workers/
    Admin de Área o Superior. Devuelve estadísticas por trabajador del área.
    AA ve solo su área; SA puede filtrar por ?area=<uuid>.
    """
    permission_classes = [IsAdminAreaOrAbove]

    def get(self, request):
        user = request.user

        if user.role == 'admin_area':
            area = get_object_or_404(Area, pk=user.area_id)
        else:
            area_pk = request.query_params.get('area')
            if not area_pk:
                return Response(
                    {'detail': 'Parámetro "area" requerido para Super Admin.'},
                    status=400,
                )
            area = get_object_or_404(Area, pk=area_pk)

        workers_qs = User.objects.filter(area=area, role='trabajador').annotate(
            total_owned=Count('owned_activities', filter=Q(owned_activities__area=area)),
            total_assigned=Count('assigned_activities', filter=Q(assigned_activities__area=area)),
            total_completed=Count(
                'owned_activities',
                filter=Q(owned_activities__area=area, owned_activities__status='completed'),
            ),
        )

        workers = [
            {
                'user_id':        str(w.id),
                'email':          w.email,
                'full_name':      w.full_name,
                'total_owned':    w.total_owned,
                'total_assigned': w.total_assigned,
                'completed':      w.total_completed,
                'completion_rate': (
                    round(w.total_completed / w.total_owned * 100, 1)
                    if w.total_owned > 0 else 0.0
                ),
            }
            for w in workers_qs
        ]

        return Response({
            'area_id':   str(area.id),
            'area_name': area.name,
            'workers':   workers,
        })
