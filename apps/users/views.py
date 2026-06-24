from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.mixins import TenantQuerySetMixin
from core.permissions import IsAdminAreaOrAbove, IsWorkerOrAbove
from .models import Invitation
from .serializers import (
    AcceptInvitationSerializer,
    InvitationCreateSerializer,
    UserDetailSerializer,
    UserListSerializer,
    VerifyInviteSerializer,
)

User = get_user_model()


class UserListView(TenantQuerySetMixin, generics.ListAPIView):
    """GET /api/users/ — list users within the same company."""
    queryset           = User.objects.all()
    serializer_class   = UserListSerializer
    permission_classes = [IsAdminAreaOrAbove]

    def get_queryset(self):
        qs          = super().get_queryset()
        user        = self.request.user
        role_filter = self.request.query_params.get('role')

        if user.role != 'super_admin':
            qs = qs.filter(area_id=user.area_id)

        if role_filter:
            qs = qs.filter(role=role_filter)
        return qs


class UserDetailView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/users/<pk>/"""
    serializer_class   = UserDetailSerializer
    permission_classes = [IsWorkerOrAbove]
    http_method_names  = ['get', 'patch', 'head', 'options']

    def _company_id(self):
        return self.request.auth.payload.get('company_id') if self.request.auth else None

    def get_object(self):
        pk         = self.kwargs['pk']
        user       = self.request.user
        company_id = self._company_id()

        target = generics.get_object_or_404(User, pk=pk, company_id=company_id)

        if user.role == 'super_admin':
            return target
        if user.role == 'admin_area':
            if target.area_id == user.area_id or target.pk == user.pk:
                return target
            from rest_framework.exceptions import NotFound
            raise NotFound()
        if target.pk != user.pk:
            from rest_framework.exceptions import NotFound
            raise NotFound()
        return target

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        instance = self.get_object()
        user     = request.user

        if user.role in ('trabajador', 'admin_area') and instance.pk != user.pk:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@method_decorator(ratelimit(key='user_or_ip', rate='10/h', block=False), name='dispatch')
class InviteView(APIView):
    """POST /api/users/invite/"""
    permission_classes = [IsAdminAreaOrAbove]

    def post(self, request):
        if getattr(request, 'limited', False):
            return Response(
                {'detail': 'Límite de invitaciones alcanzado. Intenta más tarde.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        company_id = request.auth.payload.get('company_id') if request.auth else None
        serializer = InvitationCreateSerializer(
            data=request.data,
            context={'company_id': company_id},
        )
        serializer.is_valid(raise_exception=True)

        role = serializer.validated_data.get('role')
        area = serializer.validated_data.get('area')

        if request.user.role == 'admin_area':
            if role != 'trabajador':
                return Response(
                    {'role': 'Solo puedes invitar trabajadores a tu área.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if area and area.id != request.user.area_id:
                return Response(
                    {'area': 'Solo puedes crear invitaciones para tu propia área.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        if role == 'super_admin' and request.user.role != 'super_admin':
            return Response(
                {'role': 'Solo un Super Admin puede invitar a otro Super Admin.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        from apps.companies.models import Company
        from django.shortcuts import get_object_or_404
        company = get_object_or_404(Company, id=company_id)

        result = serializer.save(created_by=request.user, company=company)
        return Response(result, status=status.HTTP_201_CREATED)


class VerifyInviteView(APIView):
    """
    GET  /api/users/invite/verify/?code=XXXXXXXX
    POST /api/users/invite/verify/
    """
    permission_classes = [AllowAny]

    def _verify(self, data):
        serializer = VerifyInviteSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        invitation = serializer.validated_data['_invitation']
        return Response({
            'role':       invitation.role,
            'area_name':  invitation.area.name if invitation.area else None,
            'expires_at': invitation.expires_at,
        })

    def get(self, request):
        return self._verify({'code': request.query_params.get('code', '')})

    def post(self, request):
        return self._verify(request.data)


class AcceptInviteView(APIView):
    """POST /api/users/accept-invite/"""
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
                'company_id': str(user.company_id) if user.company_id else None,
                'area_id':    str(user.area_id) if user.area_id else None,
            },
            status=status.HTTP_201_CREATED,
        )
