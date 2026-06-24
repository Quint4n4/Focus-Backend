from rest_framework_simplejwt.tokens import RefreshToken


class FocusRefreshToken(RefreshToken):
    """
    Extiende RefreshToken para inyectar company_id y role en el payload.
    Usar en lugar de RefreshToken.for_user() en todas las vistas de login.
    """

    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        token['company_id'] = str(user.company_id) if user.company_id else None
        token['role']       = user.role
        return token
