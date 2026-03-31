import hashlib
import secrets
import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Invitation(models.Model):
    class Role(models.TextChoices):
        ADMIN_AREA = 'admin_area', 'Admin de Área'
        TRABAJADOR = 'trabajador', 'Trabajador de Área'

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token_hash = models.CharField(max_length=64, unique=True)  # SHA-256 del token real
    area       = models.ForeignKey(
        'areas.Area',
        on_delete=models.CASCADE,
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

    @property
    def is_valid(self):
        return not self.used and self.expires_at > timezone.now()
