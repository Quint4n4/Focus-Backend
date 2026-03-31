from django.contrib.auth import get_user_model
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


def _get_activity_for_user(pk, user):
    """
    Return the Activity with the given pk if the user has read access,
    otherwise raise Http404.
    """
    activity = get_object_or_404(Activity, pk=pk)
    if user.role == 'super_admin':
        return activity
    if user.role == 'admin_area':
        if activity.area_id == user.area_id:
            return activity
        raise Activity.DoesNotExist
    # trabajador
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
        user = self.request.user
        if user.role == 'super_admin':
            return Activity.objects.all()
        if user.role == 'admin_area':
            return Activity.objects.filter(area=user.area)
        # trabajador
        return Activity.objects.filter(
            owner=user
        ) | Activity.objects.filter(assigned_to=user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


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

    def patch(self, request, pk):
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

    def patch(self, request, pk):
        activity = get_object_or_404(Activity, pk=pk)
        user = request.user

        # admin_area limited to own area
        if user.role == 'admin_area' and activity.area_id != user.area_id:
            from rest_framework.exceptions import NotFound
            raise NotFound()

        serializer = AssignActivitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assignee = serializer.validated_data['assigned_to']
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
