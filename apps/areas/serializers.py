from django.contrib.auth import get_user_model

from rest_framework import serializers

from .models import Area

User = get_user_model()


class AreaSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = Area
        fields = ['id', 'name', 'description', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def get_created_by(self, obj):
        user = obj.created_by
        if user is None:
            return None
        return {
            'id': str(user.id),
            'email': user.email,
            'full_name': user.full_name,
        }


class AreaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = ['name', 'description']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'created_at']
