from django.contrib.auth import get_user_model
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

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
    """
    Reglas de acceso para admin_area — debe mantenerse en sync con
    el queryset de ActivityListCreateView (scope team).

    Un AA puede ver una actividad si:
      1. La actividad pertenece a su área (area_id coincide).
      2. La actividad no tiene área pero pertenece a un proyecto del área del AA
         (cubre actividades históricas con area_id=null creadas en proyectos del área).
      3. El AA la creó (owner) — garantiza que el creador siempre puede ver
         lo que acaba de crear, incluso si el proyecto aún no tiene área en DB.
    """
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


def _get_activity_for_user(pk, user):
    """
    Return the Activity with the given pk if the user has read access,
    otherwise raise Http404.
    """
    activity = get_object_or_404(Activity, pk=pk)
    if user.role == 'super_admin':
        return activity
    if user.role == 'admin_area':
        if _can_aa_access_activity(activity, user):
            return activity
        raise Activity.DoesNotExist
    # trabajador/personal: propio + asignadas
    if activity.owner_id == user.pk or activity.assigned_to_id == user.pk:
        return activity
    raise Activity.DoesNotExist


class ActivityListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsWorkerOrAbove]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ActivityListSerializer
        return ActivitySerializer

    def get_queryset(self):
        user  = self.request.user
        scope = self.request.query_params.get('scope')  # 'personal' | 'team' | None

        if user.role == 'super_admin':
            qs = Activity.objects.all()
            if scope == 'personal':
                qs = qs.filter(owner=user)
            return qs

        if user.role == 'admin_area':
            if scope == 'personal':
                return Activity.objects.filter(owner=user)
            # scope='team' o sin scope → todo el área.
            # Reglas en sync con _can_aa_access_activity:
            #   1. area_id del AA
            #   2. area_id null pero project del área del AA (datos históricos)
            #   3. owner=user — creador siempre ve sus propias actividades
            return Activity.objects.filter(
                models.Q(area_id=user.area_id) |
                models.Q(area_id__isnull=True, project__area_id=user.area_id) |
                models.Q(owner=user)
            ).distinct()

        # trabajador: propio + asignadas
        qs = Activity.objects.filter(owner=user) | Activity.objects.filter(assigned_to=user)
        if scope == 'team':
            # Solo actividades del área (excluye las puramente personales)
            qs = Activity.objects.filter(area_id=user.area_id).filter(
                models.Q(owner=user) | models.Q(assigned_to=user)
            )
        elif scope == 'personal':
            qs = Activity.objects.filter(owner=user, area__isnull=True)
        return qs

    def perform_create(self, serializer):
        kwargs = {'owner': self.request.user}
        # Si la actividad se crea dentro de un proyecto que tiene área,
        # y el cliente no mandó área explícita, heredarla del proyecto.
        project = serializer.validated_data.get('project')
        area    = serializer.validated_data.get('area')
        if project and not area and project.area_id:
            kwargs['area_id'] = project.area_id
        serializer.save(**kwargs)


class ActivityDetailView(APIView):
    permission_classes = [IsWorkerOrAbove]

    def _get_activity(self, pk):
        try:
            return _get_activity_for_user(pk, self.request.user)
        except (Activity.DoesNotExist, Exception):
            from rest_framework.exceptions import NotFound
            raise NotFound()

    def get(self, request, pk):
        activity = self._get_activity(pk)
        serializer = ActivitySerializer(activity, context={'request': request})
        return Response(serializer.data)

    def patch(self, request, pk):
        activity = self._get_activity(pk)
        serializer = ActivitySerializer(
            activity, data=request.data, partial=True, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        activity._updated_by = request.user
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        activity = self._get_activity(pk)
        user = request.user
        # Only owner, admin_area of same area, or super_admin can delete
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
        try:
            activity = _get_activity_for_user(pk, request.user)
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

        # Explicit log for the move (in addition to the generic UPDATED signal log)
        ActivityLog.objects.create(
            activity=activity,
            user=request.user,
            event_type=ActivityLog.EventType.MOVED,
            detail={'from': old_status, 'to': new_status},
        )

        return Response(
            ActivitySerializer(activity, context={'request': request}).data
        )


class AssignActivityView(APIView):
    permission_classes = [IsAdminAreaOrAbove]

    def post(self, request, pk):
        from rest_framework.exceptions import NotFound, PermissionDenied

        # Reutilizar la misma función de acceso que detail/list para AA
        try:
            activity = _get_activity_for_user(pk, request.user)
        except Activity.DoesNotExist:
            raise NotFound()

        serializer = AssignActivitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assignee = serializer.validated_data['assigned_to']
        user = request.user

        # Validar que el asignatario pertenezca al área del AA.
        # SA puede asignar a cualquiera; AA solo a miembros de su área.
        if assignee is not None and user.role == 'admin_area':
            if assignee.area_id != user.area_id:
                return Response(
                    {'assigned_to': 'Solo puedes asignar actividades a miembros de tu área.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        activity.assigned_to = assignee
        activity.assigned_by = request.user
        activity._updated_by = request.user
        activity.save()

        ActivityLog.objects.create(
            activity=activity,
            user=request.user,
            event_type=ActivityLog.EventType.ASSIGNED,
            detail={'assigned_to': str(assignee.id) if assignee else None},
        )

        return Response(
            ActivitySerializer(activity, context={'request': request}).data
        )


class CompleteActivityView(APIView):
    permission_classes = [IsWorkerOrAbove]

    def post(self, request, pk):
        try:
            activity = _get_activity_for_user(pk, request.user)
        except Exception:
            from rest_framework.exceptions import NotFound
            raise NotFound()

        if activity.status == Activity.Status.COMPLETED:
            return Response(
                {'detail': 'La actividad ya está completada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        activity.status = Activity.Status.COMPLETED
        activity.completed_at = timezone.now()
        activity._updated_by = request.user
        activity.save()

        ActivityLog.objects.create(
            activity=activity,
            user=request.user,
            event_type=ActivityLog.EventType.COMPLETED,
            detail={'completed_at': str(activity.completed_at)},
        )

        return Response(
            ActivitySerializer(activity, context={'request': request}).data
        )


class AttachmentListCreateView(APIView):
    permission_classes = [IsWorkerOrAbove]
    parser_classes = [MultiPartParser, FormParser]

    def _get_activity(self, pk):
        try:
            return _get_activity_for_user(pk, self.request.user)
        except Exception:
            from rest_framework.exceptions import NotFound
            raise NotFound()

    def get(self, request, pk):
        activity = self._get_activity(pk)
        attachments = activity.attachments.all()

        # TA solo ve sus propios adjuntos
        if request.user.role not in ('super_admin', 'admin_area'):
            attachments = attachments.filter(uploaded_by=request.user)

        serializer = ActivityAttachmentSerializer(
            attachments, many=True, context={'request': request}
        )
        return Response(serializer.data)

    def post(self, request, pk):
        activity = self._get_activity(pk)
        upload_serializer = AttachmentUploadSerializer(data=request.data)
        upload_serializer.is_valid(raise_exception=True)

        attachment = ActivityAttachment.objects.create(
            activity=activity,
            file=request.FILES['file'],
            uploaded_by=request.user,
        )
        serializer = ActivityAttachmentSerializer(attachment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ServeAttachmentFileView(APIView):
    """
    GET /api/activities/<pk>/attachments/<attachment_pk>/file/
    Sirve el archivo con control de acceso:
      SA  → todos
      AA  → solo adjuntos de actividades de su área
      TA  → solo adjuntos que él mismo subió
    """
    permission_classes = [IsWorkerOrAbove]

    def get(self, request, pk, attachment_pk):
        import os
        from django.http import FileResponse
        from rest_framework.exceptions import NotFound, PermissionDenied

        activity   = get_object_or_404(Activity, pk=pk)
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
        activity = get_object_or_404(Activity, pk=pk)
        attachment = get_object_or_404(ActivityAttachment, pk=attachment_pk, activity=activity)

        user = request.user
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
        try:
            activity = _get_activity_for_user(pk, request.user)
        except Exception:
            from rest_framework.exceptions import NotFound
            raise NotFound()

        logs = activity.logs.order_by('-created_at')
        serializer = ActivityLogSerializer(logs, many=True, context={'request': request})
        return Response(serializer.data)
