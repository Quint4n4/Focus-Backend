from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.areas.models import Area

from .models import Project

User = get_user_model()


class ProjectSerializer(serializers.ModelSerializer):
    """Full read serializer."""
    created_by      = serializers.SerializerMethodField()
    # 'area' como clave JSON (Flutter lo lee como 'area', no 'area_id')
    area            = serializers.UUIDField(source='area_id', read_only=True, allow_null=True)
    area_name       = serializers.SerializerMethodField()
    area_admin_name = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description',
            'area', 'area_name', 'area_admin_name',
            'created_by', 'status', 'target_date',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_by', 'area', 'area_name', 'area_admin_name',
            'created_at', 'updated_at',
        ]

    def get_created_by(self, obj):
        user = obj.created_by
        if user is None:
            return None
        return {'id': str(user.id), 'email': user.email}

    def get_area_name(self, obj):
        # area está en select_related — sin query extra
        return obj.area.name if obj.area_id and obj.area else None

    def get_area_admin_name(self, obj):
        if not obj.area_id:
            return None
        # Usa area_id directo (sin cargar area FK de nuevo)
        admin = User.objects.filter(
            area_id=obj.area_id, role='admin_area'
        ).values('first_name', 'last_name').first()
        if admin:
            return f"{admin['first_name']} {admin['last_name']}".strip() or None
        return None


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

    def to_internal_value(self, data):
        # El cliente puede enviar 'area_id' (igual que el campo de lectura).
        # Normalizar a 'area' para que PrimaryKeyRelatedField lo procese.
        if 'area_id' in data and 'area' not in data:
            data = data.copy()
            data['area'] = data['area_id']
        return super().to_internal_value(data)

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
