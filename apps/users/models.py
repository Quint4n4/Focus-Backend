import hashlib
import secrets
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Invitation(models.Model):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super Admin'
        ADMIN_AREA  = 'admin_area',  'Admin de Área'
        TRABAJADOR  = 'trabajador',  'Trabajador de Área'

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token_hash = models.CharField(max_length=64, unique=True)  # SHA-256 del token real
    code       = models.CharField(max_length=16, unique=True, null=True, blank=True)  # código corto legible
    area       = models.ForeignKey(
        'areas.Area',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='invitations',
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.TRABAJADOR,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_invitations',
    )
    expires_at = models.DateTimeField()
    used       = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Invitación'
        verbose_name_plural = 'Invitaciones'
        ordering            = ['-created_at']

    @classmethod
    def generate_token(cls):
        """Genera un token aleatorio y devuelve (raw_token, token_hash)."""
        raw    = secrets.token_urlsafe(32)
        hashed = hashlib.sha256(raw.encode()).hexdigest()
        return raw, hashed

    @classmethod
    def hash_token(cls, raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode()).hexdigest()

    @classmethod
    def generate_code(cls) -> str:
        """Genera un código corto único de 8 chars (ej. XK92BLP3)."""
        import string
        alphabet = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(secrets.choice(alphabet) for _ in range(8))
            if not cls.objects.filter(code=code).exists():
                return code

    @property
    def is_valid(self):
        return not self.used and self.expires_at > timezone.now()
