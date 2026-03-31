from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from rest_framework import generics, status
from rest_framework.response import Response

from core.permissions import IsSuperAdmin, IsWorkerOrAbove

from .models import Area
from .serializers import AreaCreateSerializer, AreaSerializer, MemberSerializer

User = get_user_model()


class AreaListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/areas/  — list areas (IsWorkerOrAbove)
    POST /api/areas/  — create area (IsSuperAdmin only)
    """

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsSuperAdmin()]
        return [IsWorkerOrAbove()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AreaCreateSerializer
        return AreaSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Area.objects.all()
        # admin_area and trabajador: only their own area
        if user.area_id is not None:
            return Area.objects.filter(id=user.area_id)
        return Area.objects.none()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Return full representation using AreaSerializer
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
        pk = self.kwargs['pk']
        return get_object_or_404(Area, pk=pk)


class AreaMembersView(generics.ListAPIView):
    """
    GET /api/areas/<pk>/members/
    Super admin: any area; admin_area and trabajador: only their own area.
    """
    serializer_class = MemberSerializer
    permission_classes = [IsWorkerOrAbove]

    def get_queryset(self):
        pk = self.kwargs['pk']
        area = get_object_or_404(Area, pk=pk)
        user = self.request.user

        # Non-super-admin users can only view members of their own area
        if user.role != 'super_admin':
            if user.area_id is None or str(user.area_id) != str(area.pk):
                return User.objects.none()

        return User.objects.filter(area=area)
