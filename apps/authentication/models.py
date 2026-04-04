import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):

    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super Admin'
        ADMIN_AREA  = 'admin_area',  'Admin de Área'
        TRABAJADOR  = 'trabajador',  'Trabajador de Área'
        PERSONAL    = 'personal',    'Personal'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name  = models.CharField(max_length=150)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.TRABAJADOR,
    )
    area = models.ForeignKey(
        'areas.Area',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
    )

    is_active = models.BooleanField(default=True)
    is_staff  = models.BooleanField(default=False)

    biometrics_enabled   = models.BooleanField(default=False)
    device_id            = models.CharField(max_length=255, blank=True, null=True)
    onboarding_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    class Meta:
        verbose_name  = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['email']

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN

    @property
    def is_admin_area(self):
        return self.role == self.Role.ADMIN_AREA

    @property
    def is_trabajador(self):
        return self.role == self.Role.TRABAJADOR

    @property
    def is_personal(self):
        return self.role == self.Role.PERSONAL

    @property
    def is_org_user(self):
        """True si pertenece a una organización (tiene área asignada)."""
        return self.role in (self.Role.SUPER_ADMIN, self.Role.ADMIN_AREA, self.Role.TRABAJADOR)
