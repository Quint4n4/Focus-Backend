from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from rest_framework import generics, status
from rest_framework.response import Response

from core.mixins import TenantQuerySetMixin
from core.permissions import IsSuperAdmin, IsWorkerOrAbove

from .models import Area
from .serializers import AreaCreateSerializer, AreaSerializer, MemberSerializer

User = get_user_model()


class AreaListCreateView(TenantQuerySetMixin, generics.ListCreateAPIView):
    """
    GET  /api/areas/  — list areas (IsWorkerOrAbove)
    POST /api/areas/  — create area (IsSuperAdmin only)
    """
    queryset = Area.objects.all()

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsSuperAdmin()]
        return [IsWorkerOrAbove()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AreaCreateSerializer
        return AreaSerializer

    def get_queryset(self):
        # TenantQuerySetMixin filtra por company_id; aquí refinamos por rol.
        qs = super().get_queryset()
        user = self.request.user
        if user.role == 'super_admin':
            return qs
        if user.area_id is not None:
            return qs.filter(id=user.area_id)
        return qs.none()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, company=self.get_company())

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        area = Area.objects.get(pk=serializer.instance.pk)
        output = AreaSerializer(area, context={'request': request})
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)


class AreaDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/areas/<pk>/  — IsWorkerOrAbove
    PUT    /api/areas/<pk>/  — IsSuperAdmin
    PATCH  /api/areas/<pk>/  — IsSuperAdmin
    DELETE /api/areas/<pk>/  — IsSuperAdmin
    """
    serializer_class = AreaSerializer
    lookup_field = 'pk'

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsSuperAdmin()]
        return [IsWorkerOrAbove()]

    def get_object(self):
        pk         = self.kwargs['pk']
        company_id = self.request.auth.payload.get('company_id') if self.request.auth else None
        return get_object_or_404(Area, pk=pk, company_id=company_id)


class AreaMembersView(generics.ListAPIView):
    """
    GET /api/areas/<pk>/members/
    Super admin: any area (in own company); admin_area and trabajador: only their area.
    """
    serializer_class   = MemberSerializer
    permission_classes = [IsWorkerOrAbove]

    def get_queryset(self):
        pk         = self.kwargs['pk']
        company_id = self.request.auth.payload.get('company_id') if self.request.auth else None
        area       = get_object_or_404(Area, pk=pk, company_id=company_id)
        user       = self.request.user

        if user.role != 'super_admin':
            if user.area_id is None or str(user.area_id) != str(area.pk):
                return User.objects.none()

        return User.objects.filter(area=area, company_id=company_id)
