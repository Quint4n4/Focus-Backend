from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import Activity, ActivityLog

# Flag to prevent recursive signal loops during log creation
_creating_log = False


@receiver(post_save, sender=Activity)
def log_activity_save(sender, instance, created, **kwargs):
    global _creating_log
    if _creating_log:
        return
    _creating_log = True
    try:
        if created:
            ActivityLog.objects.create(
                activity=instance,
                user=instance.owner,
                event_type=ActivityLog.EventType.CREATED,
                detail={'title': instance.title, 'status': instance.status},
            )
        else:
            ActivityLog.objects.create(
                activity=instance,
                user=getattr(instance, '_updated_by', instance.owner),
                event_type=ActivityLog.EventType.UPDATED,
                detail={'title': instance.title, 'status': instance.status},
            )
    finally:
        _creating_log = False


@receiver(pre_delete, sender=Activity)
def log_activity_delete(sender, instance, **kwargs):
    global _creating_log
    if _creating_log:
        return
    _creating_log = True
    try:
        ActivityLog.objects.create(
            activity=instance,
            user=getattr(instance, '_deleted_by', instance.owner),
            event_type=ActivityLog.EventType.DELETED,
            detail={'title': instance.title},
        )
    finally:
        _creating_log = False
