from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.areas.models import Area

from .models import Project

User = get_user_model()


class ProjectSerializer(serializers.ModelSerializer):
    """Full read serializer."""
    created_by = serializers.SerializerMethodField()
    area_id = serializers.UUIDField(source='area_id', read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'area_id', 'created_by',
                  'status', 'target_date', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'area_id', 'created_at', 'updated_at']

    def get_created_by(self, obj):
        user = obj.created_by
        if user is None:
            return None
        return {'id': str(user.id), 'email': user.email}


class ProjectCreateSerializer(serializers.ModelSerializer):
    """Write serializer for creating/updating projects."""
    area = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Project
        fields = ['name', 'description', 'area', 'status', 'target_date']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class ProjectProgressSerializer(serializers.Serializer):
    """Read-only output for progress endpoint."""
    total                 = serializers.IntegerField(read_only=True)
    completed             = serializers.IntegerField(read_only=True)
    pending               = serializers.IntegerField(read_only=True)
    in_progress           = serializers.IntegerField(read_only=True)
    completion_percentage = serializers.FloatField(read_only=True)
