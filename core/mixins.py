from django.shortcuts import get_object_or_404


class TenantQuerySetMixin:
    """
    Filtra automáticamente todos los querysets por la empresa del token JWT.
    Incluir como primer padre en cualquier view genérica o APIView que opere
    sobre modelos con FK a Company.

    Las vistas que sobreescriban get_queryset() deben llamar a
    super().get_queryset() para obtener el queryset base ya filtrado,
    o aplicar .filter(company_id=self.get_company_id()) manualmente.
    """

    def get_company_id(self):
        """Extrae company_id del payload del token JWT."""
        if not hasattr(self.request, 'auth') or self.request.auth is None:
            return None
        return self.request.auth.payload.get('company_id')

    def get_company(self):
        """Devuelve el objeto Company; lo cachea en request para evitar queries repetidas."""
        if not hasattr(self.request, '_company'):
            from apps.companies.models import Company
            company_id = self.get_company_id()
            self.request._company = get_object_or_404(Company, id=company_id)
        return self.request._company

    def get_queryset(self):
        qs = super().get_queryset()
        company_id = self.get_company_id()
        if company_id:
            return qs.filter(company_id=company_id)
        return qs.none()

    def perform_create(self, serializer):
        serializer.save(company=self.get_company())
