from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsAdminAreaOrAbove, IsWorkerOrAbove
from .models import Invitation
from .serializers import (
    AcceptInvitationSerializer,
    InvitationCreateSerializer,
    UserDetailSerializer,
    UserListSerializer,
)

User = get_user_model()


class UserListView(generics.ListAPIView):
    """GET /api/users/ — list users. Requires admin_area or above."""

    serializer_class   = UserListSerializer
    permission_classes = [IsAdminAreaOrAbove]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return User.objects.all()
        # admin_area: only members of their own area
        return User.objects.filter(area=user.area)


class UserDetailView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/users/<pk>/"""

    serializer_class   = UserDetailSerializer
    permission_classes = [IsWorkerOrAbove]
    http_method_names  = ['get', 'patch', 'head', 'options']

    def get_object(self):
        pk   = self.kwargs['pk']
        user = self.request.user

        # Fetch the target user or return 404
        target = generics.get_object_or_404(User, pk=pk)

        if user.role == 'super_admin':
            return target

        if user.role == 'admin_area':
            # Admin can see anyone in their area or themselves
            if target.area_id == user.area_id or target.pk == user.pk:
                return target
            # Otherwise 404 (don't leak existence)
            from rest_framework.exceptions import NotFound
            raise NotFound()

        # trabajador: only themselves
        if target.pk != user.pk:
            from rest_framework.exceptions import NotFound
            raise NotFound()

        return target

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        instance = self.get_object()
        user     = request.user

        # Workers can only edit themselves; super_admin can edit anyone
        if user.role == 'trabajador' and instance.pk != user.pk:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()

        if user.role == 'admin_area' and instance.pk != user.pk:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@method_decorator(ratelimit(key='user_or_ip', rate='10/h', block=False), name='dispatch')
class InviteView(APIView):
    """POST /api/users/invite/ — create an invitation link."""

    permission_classes = [IsAdminAreaOrAbove]

    def post(self, request):
        if getattr(request, 'limited', False):
            return Response({'detail': 'Límite de invitaciones alcanzado. Intenta más tarde.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # admin_area can only invite to their own area
        if request.user.role == 'admin_area':
            area = serializer.validated_data.get('area')
            if area and area.id != request.user.area_id:
                return Response(
                    {'area': 'Solo puedes crear invitaciones para tu propia área.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        result = serializer.save(created_by=request.user)
        return Response(result, status=status.HTTP_201_CREATED)


class AcceptInviteView(APIView):
    """POST /api/users/accept-invite/ — accept an invitation and create a user."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'id':         str(user.id),
                'email':      user.email,
                'first_name': user.first_name,
                'last_name':  user.last_name,
                'role':       user.role,
            },
            status=status.HTTP_201_CREATED,
        )
