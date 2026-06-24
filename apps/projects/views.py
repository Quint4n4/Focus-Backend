from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from core.mixins import TenantQuerySetMixin
from core.permissions import IsAdminAreaOrAbove, IsWorkerOrAbove
from .models import Project
from .serializers import ProjectSerializer, ProjectCreateSerializer, ProjectProgressSerializer

User = get_user_model()


def _get_project_for_user(pk, user, company_id):
    """Return Project if user has access within their company, raise NotFound otherwise."""
    project = get_object_or_404(
        Project.objects.select_related('created_by', 'area'),
        pk=pk,
        company_id=company_id,
    )
    if user.role == 'super_admin':
        return project
    if project.area_id is None and project.created_by_id == user.pk:
        return project
    if project.area_id is not None and project.area_id == user.area_id:
        return project
    raise NotFound()


class ProjectListCreateView(TenantQuerySetMixin, generics.ListCreateAPIView):
    """
    GET  /api/projects/  — list projects (IsWorkerOrAbove)
    POST /api/projects/  — create project (IsWorkerOrAbove)
    """
    queryset           = Project.objects.all()
    permission_classes = [IsWorkerOrAbove]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProjectCreateSerializer
        return ProjectSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['company_id'] = self.get_company_id()
        return ctx

    def get_queryset(self):
        qs   = super().get_queryset().select_related('created_by', 'area')
        user = self.request.user
        if user.role == 'super_admin':
            return qs
        return qs.filter(
            Q(area_id=user.area_id) | Q(area_id__isnull=True, created_by=user)
        )

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, company=self.get_company())

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        area = serializer.validated_data.get('area')

        if request.user.role in ('trabajador', 'personal') and area is not None:
            return Response(
                {'area': 'Solo puedes crear proyectos personales (sin área).'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if request.user.role == 'admin_area' and area is not None:
            if str(area.id) != str(request.user.area_id):
                return Response(
                    {'area': 'Solo puedes crear proyectos en tu propia área.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        self.perform_create(serializer)
        output = ProjectSerializer(serializer.instance, context={'request': request})
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)


class ProjectDetailView(APIView):
    """
    GET    /api/projects/<pk>/  — retrieve project (IsWorkerOrAbove)
    PATCH  /api/projects/<pk>/  — partial update (IsAdminAreaOrAbove)
    DELETE /api/projects/<pk>/  — delete project (IsAdminAreaOrAbove)
    """
    permission_classes = [IsWorkerOrAbove]

    def _company_id(self):
        return self.request.auth.payload.get('company_id') if self.request.auth else None

    def get(self, request, pk):
        project = _get_project_for_user(pk, request.user, self._company_id())
        return Response(ProjectSerializer(project, context={'request': request}).data)

    def patch(self, request, pk):
        project = _get_project_for_user(pk, request.user, self._company_id())
        if request.user.role == 'trabajador':
            raise PermissionDenied()
        serializer = ProjectCreateSerializer(
            project, data=request.data, partial=True, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProjectSerializer(serializer.instance, context={'request': request}).data)

    def delete(self, request, pk):
        project = _get_project_for_user(pk, request.user, self._company_id())
        if request.user.role == 'trabajador':
            raise PermissionDenied()
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectActivitiesView(APIView):
    """GET /api/projects/<pk>/activities/"""
    permission_classes = [IsWorkerOrAbove]

    def get(self, request, pk):
        from django.db.models import Q as DQ
        from apps.activities.models import Activity
        from apps.activities.serializers import ActivityListSerializer
        from rest_framework.pagination import PageNumberPagination

        company_id = request.auth.payload.get('company_id') if request.auth else None
        project    = _get_project_for_user(pk, request.user, company_id)
        user       = request.user

        qs = project.activities.order_by('-created_at')
        if user.role not in ('super_admin', 'admin_area'):
            qs = qs.filter(DQ(owner=user) | DQ(assigned_to=user))

        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs, request)
        serializer = ActivityListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ProjectProgressView(APIView):
    """GET /api/projects/<pk>/progress/"""
    permission_classes = [IsWorkerOrAbove]

    def get(self, request, pk):
        company_id = request.auth.payload.get('company_id') if request.auth else None
        project    = _get_project_for_user(pk, request.user, company_id)
        qs         = project.activities.all()
        total      = qs.count()
        completed  = qs.filter(status='completed').count()
        pending    = qs.filter(status='pending').count()
        in_progress = qs.exclude(status__in=['completed', 'inbox']).count()
        data = {
            'total': total,
            'completed': completed,
            'pending': pending,
            'in_progress': in_progress,
            'completion_percentage': round(completed / total * 100, 1) if total > 0 else 0.0,
        }
        return Response(ProjectProgressSerializer(data).data)
