from django.contrib.auth import get_user_model
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.mixins import TenantQuerySetMixin
from core.permissions import IsSuperAdmin, IsAdminAreaOrAbove, IsWorkerOrAbove
from .models import Activity, ActivityLog, ActivityAttachment
from .serializers import (
    ActivitySerializer,
    ActivityListSerializer,
    MoveActivitySerializer,
    AssignActivitySerializer,
    ActivityLogSerializer,
    ActivityAttachmentSerializer,
    AttachmentUploadSerializer,
)

User = get_user_model()


def _can_aa_access_activity(activity, user):
    if activity.area_id and activity.area_id == user.area_id:
        return True
    if activity.owner_id == user.pk:
        return True
    if activity.area_id is None and activity.project_id:
        from apps.projects.models import Project
        return Project.objects.filter(
            pk=activity.project_id, area_id=user.area_id
        ).exists()
    return False


def _get_activity_for_user(pk, user, company_id):
    """Return Activity within company if user has access, else raise Http404."""
    activity = get_object_or_404(Activity, pk=pk, company_id=company_id)
    if user.role == 'super_admin':
        return activity
    if user.role == 'admin_area':
        if _can_aa_access_activity(activity, user):
            return activity
        raise Activity.DoesNotExist
    if activity.owner_id == user.pk or activity.assigned_to_id == user.pk:
        return activity
    raise Activity.DoesNotExist


class ActivityListCreateView(TenantQuerySetMixin, generics.ListCreateAPIView):
    queryset           = Activity.objects.all()
    permission_classes = [IsWorkerOrAbove]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ActivityListSerializer
        return ActivitySerializer

    def get_queryset(self):
        qs    = super().get_queryset()
        user  = self.request.user
        scope = self.request.query_params.get('scope')

        if user.role == 'super_admin':
            if scope == 'personal':
                return qs.filter(owner=user)
            return qs

        if user.role == 'admin_area':
            if scope == 'personal':
                return qs.filter(owner=user)
            return qs.filter(
                models.Q(area_id=user.area_id) |
                models.Q(area_id__isnull=True, project__area_id=user.area_id) |
                models.Q(owner=user)
            ).distinct()

        # trabajador/personal
        qs_own      = qs.filter(owner=user)
        qs_assigned = qs.filter(assigned_to=user)
        if scope == 'team':
            return qs.filter(area_id=user.area_id).filter(
                models.Q(owner=user) | models.Q(assigned_to=user)
            )
        elif scope == 'personal':
            return qs.filter(owner=user, area__isnull=True)
        return (qs_own | qs_assigned).distinct()

    def perform_create(self, serializer):
        company = self.get_company()
        kwargs  = {'owner': self.request.user, 'company': company}
        project = serializer.validated_data.get('project')
        area    = serializer.validated_data.get('area')
        if project and not area and project.area_id:
            kwargs['area_id'] = project.area_id
        serializer.save(**kwargs)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['company_id'] = self.get_company_id()
        return ctx


class ActivityDetailView(APIView):
    permission_classes = [IsWorkerOrAbove]

    def _company_id(self):
        return self.request.auth.payload.get('company_id') if self.request.auth else None

    def _get_activity(self, pk):
        try:
            return _get_activity_for_user(pk, self.request.user, self._company_id())
        except (Activity.DoesNotExist, Exception):
            from rest_framework.exceptions import NotFound
            raise NotFound()

    def get(self, request, pk):
        activity = self._get_activity(pk)
        return Response(ActivitySerializer(activity, context={'request': request}).data)

    def patch(self, request, pk):
        activity = self._get_activity(pk)
        serializer = ActivitySerializer(
            activity, data=request.data, partial=True,
            context={'request': request, 'company_id': self._company_id()}
        )
        serializer.is_valid(raise_exception=True)
        activity._updated_by = request.user
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        activity = self._get_activity(pk)
        user = request.user
        can_delete = (
            user.role == 'super_admin'
            or (user.role == 'admin_area' and activity.area_id == user.area_id)
            or activity.owner_id == user.pk
        )
        if not can_delete:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()
        activity._deleted_by = request.user
        activity.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MoveActivityView(APIView):
    permission_classes = [IsWorkerOrAbove]

    def post(self, request, pk):
        company_id = request.auth.payload.get('company_id') if request.auth else None
        try:
            activity = _get_activity_for_user(pk, request.user, company_id)
        except Exception:
            from rest_framework.exceptions import NotFound
            raise NotFound()

        serializer = MoveActivitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        old_status = activity.status
        new_status = serializer.validated_data['status']
        activity.status = new_status
        if new_status == Activity.Status.COMPLETED:
            activity.completed_at = timezone.now()
        activity._updated_by = request.user
        activity.save()

        ActivityLog.objects.create(
            activity=activity, user=request.user,
            event_type=ActivityLog.EventType.MOVED,
            detail={'from': old_status, 'to': new_status},
        )
        return Response(ActivitySerializer(activity, context={'request': request}).data)


class AssignActivityView(APIView):
    permission_classes = [IsAdminAreaOrAbove]

    def post(self, request, pk):
        from rest_framework.exceptions import NotFound, PermissionDenied
        company_id = request.auth.payload.get('company_id') if request.auth else None
        try:
            activity = _get_activity_for_user(pk, request.user, company_id)
        except Activity.DoesNotExist:
            raise NotFound()

        serializer = AssignActivitySerializer(
            data=request.data,
            context={'request': request, 'company_id': company_id},
        )
        serializer.is_valid(raise_exception=True)

        assignee = serializer.validated_data['assigned_to']
        user     = request.user

        if assignee is not None and user.role == 'admin_area':
            if assignee.area_id != user.area_id:
                return Response(
                    {'assigned_to': 'Solo puedes asignar actividades a miembros de tu área.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Verificar que el asignatario pertenezca a la misma empresa
        if assignee is not None and str(assignee.company_id) != str(company_id):
            return Response(
                {'assigned_to': 'El usuario no pertenece a tu empresa.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        activity.assigned_to = assignee
        activity.assigned_by = request.user
        activity._updated_by = request.user
        activity.save()

        ActivityLog.objects.create(
            activity=activity, user=request.user,
            event_type=ActivityLog.EventType.ASSIGNED,
            detail={'assigned_to': str(assignee.id) if assignee else None},
        )
        return Response(ActivitySerializer(activity, context={'request': request}).data)


class CompleteActivityView(APIView):
    permission_classes = [IsWorkerOrAbove]

    def post(self, request, pk):
        company_id = request.auth.payload.get('company_id') if request.auth else None
        try:
            activity = _get_activity_for_user(pk, request.user, company_id)
        except Exception:
            from rest_framework.exceptions import NotFound
            raise NotFound()

        if activity.status == Activity.Status.COMPLETED:
            return Response(
                {'detail': 'La actividad ya está completada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        activity.status       = Activity.Status.COMPLETED
        activity.completed_at = timezone.now()
        activity._updated_by  = request.user
        activity.save()

        ActivityLog.objects.create(
            activity=activity, user=request.user,
            event_type=ActivityLog.EventType.COMPLETED,
            detail={'completed_at': str(activity.completed_at)},
        )
        return Response(ActivitySerializer(activity, context={'request': request}).data)


class AttachmentListCreateView(APIView):
    permission_classes = [IsWorkerOrAbove]
    parser_classes     = [MultiPartParser, FormParser]

    def _company_id(self):
        return self.request.auth.payload.get('company_id') if self.request.auth else None

    def _get_activity(self, pk):
        try:
            return _get_activity_for_user(pk, self.request.user, self._company_id())
        except Exception:
            from rest_framework.exceptions import NotFound
            raise NotFound()

    def get(self, request, pk):
        activity    = self._get_activity(pk)
        attachments = activity.attachments.all()
        if request.user.role not in ('super_admin', 'admin_area'):
            attachments = attachments.filter(uploaded_by=request.user)
        return Response(
            ActivityAttachmentSerializer(attachments, many=True, context={'request': request}).data
        )

    def post(self, request, pk):
        activity = self._get_activity(pk)
        upload_serializer = AttachmentUploadSerializer(data=request.data)
        upload_serializer.is_valid(raise_exception=True)
        attachment = ActivityAttachment.objects.create(
            activity=activity,
            file=request.FILES['file'],
            uploaded_by=request.user,
        )
        return Response(
            ActivityAttachmentSerializer(attachment, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class ServeAttachmentFileView(APIView):
    permission_classes = [IsWorkerOrAbove]

    def get(self, request, pk, attachment_pk):
        import os
        from django.http import FileResponse
        from rest_framework.exceptions import NotFound, PermissionDenied

        company_id = request.auth.payload.get('company_id') if request.auth else None
        activity   = get_object_or_404(Activity, pk=pk, company_id=company_id)
        attachment = get_object_or_404(ActivityAttachment, pk=attachment_pk, activity=activity)
        user       = request.user

        if user.role == 'super_admin':
            pass
        elif user.role == 'admin_area':
            if activity.area_id != user.area_id:
                raise NotFound()
        else:
            if attachment.uploaded_by_id != user.pk:
                raise PermissionDenied()

        response = FileResponse(attachment.file.open('rb'))
        response['Content-Disposition'] = (
            f'inline; filename="{os.path.basename(attachment.file.name)}"'
        )
        return response


class AttachmentDeleteView(APIView):
    permission_classes = [IsWorkerOrAbove]

    def delete(self, request, pk, attachment_pk):
        company_id = request.auth.payload.get('company_id') if request.auth else None
        activity   = get_object_or_404(Activity, pk=pk, company_id=company_id)
        attachment = get_object_or_404(ActivityAttachment, pk=attachment_pk, activity=activity)
        user       = request.user

        can_delete = (
            user.role == 'super_admin'
            or (user.role == 'admin_area' and activity.area_id == user.area_id)
            or attachment.uploaded_by_id == user.pk
        )
        if not can_delete:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()

        attachment.file.delete(save=False)
        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ActivityLogListView(APIView):
    permission_classes = [IsWorkerOrAbove]

    def get(self, request, pk):
        company_id = request.auth.payload.get('company_id') if request.auth else None
        try:
            activity = _get_activity_for_user(pk, request.user, company_id)
        except Exception:
            from rest_framework.exceptions import NotFound
            raise NotFound()
        logs = activity.logs.order_by('-created_at')
        return Response(
            ActivityLogSerializer(logs, many=True, context={'request': request}).data
        )
