import uuid
from django.conf import settings
from django.db import models


class Project(models.Model):

    class Status(models.TextChoices):
        ACTIVE   = 'active',   'Activo'
        ARCHIVED = 'archived', 'Archivado'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    area        = models.ForeignKey(
        'areas.Area',
        on_delete=models.CASCADE,
        related_name='projects',
        null=True, blank=True,
    )
    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_projects',
    )
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    target_date = models.DateField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
