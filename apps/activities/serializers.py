from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.areas.models import Area
from .models import Activity, ActivityLog, ActivityAttachment

User = get_user_model()

try:
    from apps.projects.models import Project as _Project
    _HAS_PROJECT = True
except Exception:
    _Project = None
    _HAS_PROJECT = False


class _UserMiniSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    full_name = serializers.CharField()


class _UserTinySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()


class ActivitySerializer(serializers.ModelSerializer):
    owner = _UserMiniSerializer(read_only=True)
    assigned_to = serializers.PrimaryKeyRelatedField(
        allow_null=True,
        required=False,
        queryset=User.objects.all(),
    )
    assigned_by = _UserMiniSerializer(read_only=True)
    area = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(),
        required=False,
        allow_null=True,
    )
    project = (
        serializers.PrimaryKeyRelatedField(
            allow_null=True,
            required=False,
            queryset=_Project.objects.all(),
        )
        if _HAS_PROJECT
        else serializers.UUIDField(allow_null=True, required=False)
    )

    class Meta:
        model = Activity
        fields = [
            'id', 'title', 'description', 'status',
            'owner', 'assigned_to', 'assigned_by',
            'area', 'project',
            'target_date', 'completed_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'owner', 'assigned_by', 'completed_at', 'created_at', 'updated_at',
        ]


class ActivityListSerializer(serializers.ModelSerializer):
    owner_id = serializers.UUIDField(read_only=True)
    assigned_to_id = serializers.UUIDField(read_only=True, allow_null=True)
    area_id = serializers.UUIDField(read_only=True, allow_null=True)
    project_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = Activity
        fields = [
            'id', 'title', 'status',
            'owner_id', 'assigned_to_id', 'area_id', 'project_id',
            'target_date', 'completed_at', 'created_at',
        ]


class MoveActivitySerializer(serializers.Serializer):
    STATUS_CHOICES = Activity.Status.choices

    status = serializers.ChoiceField(choices=Activity.Status.choices)

    def validate_status(self, value):
        valid = [c[0] for c in Activity.Status.choices]
        if value not in valid:
            raise serializers.ValidationError(
                f'Estado inválido. Opciones válidas: {valid}'
            )
        return value


class AssignActivitySerializer(serializers.Serializer):
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        allow_null=True,
    )


class ActivityLogSerializer(serializers.ModelSerializer):
    user = _UserTinySerializer(read_only=True)

    class Meta:
        model = ActivityLog
        fields = ['id', 'user', 'event_type', 'detail', 'created_at']


class ActivityAttachmentSerializer(serializers.ModelSerializer):
    file = serializers.FileField(use_url=True)
    uploaded_by = _UserTinySerializer(read_only=True)

    class Meta:
        model = ActivityAttachment
        fields = ['id', 'file', 'uploaded_by', 'created_at']


class AttachmentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
