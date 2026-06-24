from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.serializers import UserSerializer
from apps.authentication.tokens import FocusRefreshToken
from core.permissions import IsSuperAdmin

from .models import Company
from .serializers import CompanyRegistrationSerializer, CompanySerializer


@method_decorator(ratelimit(key='ip', rate='3/h', block=True), name='dispatch')
class CompanyRegisterView(APIView):
    """
    POST /api/companies/register/
    Crea una nueva empresa y su primer super_admin. Endpoint público.
    Rate limited: 3 registros/hora por IP.
    """
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        serializer = CompanyRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company, user = serializer.save()

        refresh = FocusRefreshToken.for_user(user)

        return Response({
            'company': CompanySerializer(company).data,
            'user':    UserSerializer(user).data,
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)


class CompanyMeView(APIView):
    """
    GET   /api/companies/me/ — datos de la empresa del usuario autenticado
    PATCH /api/companies/me/ — actualizar nombre (solo super_admin)
    """
    permission_classes = [IsSuperAdmin]

    def _get_company(self, request):
        company_id = request.auth.payload.get('company_id') if request.auth else None
        from django.shortcuts import get_object_or_404
        return get_object_or_404(Company, id=company_id)

    def get(self, request):
        company = self._get_company(request)
        return Response(CompanySerializer(company).data)

    def patch(self, request):
        company    = self._get_company(request)
        serializer = CompanySerializer(company, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
