import uuid
from django.conf import settings
from django.db import models


class Activity(models.Model):

    class Status(models.TextChoices):
        INBOX     = 'inbox',      'Bandeja de entrada'
        TODAY     = 'today',      'Hoy'
        TOMORROW  = 'tomorrow',   'Mañana'
        SCHEDULED = 'scheduled',  'Programada'
        PENDING   = 'pending',    'Pendiente'
        COMPLETED = 'completed',  'Completada'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title       = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.INBOX)

    owner       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name='owned_activities')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='assigned_activities')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='activities_assigned_by')

    area        = models.ForeignKey('areas.Area', on_delete=models.CASCADE,
                                    related_name='activities')
    project     = models.ForeignKey('projects.Project', on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='activities')

    target_date  = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Actividad'
        verbose_name_plural = 'Actividades'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ActivityLog(models.Model):

    class EventType(models.TextChoices):
        CREATED   = 'created',   'Creada'
        UPDATED   = 'updated',   'Actualizada'
        MOVED     = 'moved',     'Movida de estado'
        ASSIGNED  = 'assigned',  'Asignada'
        COMPLETED = 'completed', 'Completada'
        DELETED   = 'deleted',   'Eliminada'

    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='logs')
    user     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                 null=True, related_name='activity_logs')
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    detail     = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Registro de actividad'
        verbose_name_plural = 'Registros de actividad'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.event_type} — {self.activity_id}'


class ActivityAttachment(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activity    = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='attachments')
    file        = models.FileField(upload_to='activity_attachments/%Y/%m/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, related_name='uploaded_attachments')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Adjunto'
        verbose_name_plural = 'Adjuntos'
        ordering = ['-created_at']

    def __str__(self):
        return f'Adjunto de {self.activity_id}'
