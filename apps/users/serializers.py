from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from apps.areas.models import Area
from .models import Invitation

User = get_user_model()


class UserListSerializer(serializers.ModelSerializer):
    area_id = serializers.UUIDField(read_only=True)

    class Meta:
        model  = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'area_id', 'created_at']
        read_only_fields = fields


class UserDetailSerializer(serializers.ModelSerializer):
    area_id = serializers.UUIDField(read_only=True)

    class Meta:
        model  = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role',
            'area_id', 'biometrics_enabled', 'onboarding_completed',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'email', 'role', 'area_id',
            'biometrics_enabled', 'onboarding_completed',
            'created_at', 'updated_at',
        ]


class InvitationCreateSerializer(serializers.Serializer):
    area = serializers.PrimaryKeyRelatedField(queryset=Area.objects.all())
    role = serializers.ChoiceField(
        choices=Invitation.Role.choices,
        default=Invitation.Role.TRABAJADOR,
    )

    def save(self, created_by):
        area       = self.validated_data['area']
        role       = self.validated_data['role']
        raw_token, token_hash = Invitation.generate_token()
        expires_at = timezone.now() + timedelta(hours=24)

        invitation = Invitation.objects.create(
            token_hash=token_hash,
            area=area,
            role=role,
            created_by=created_by,
            expires_at=expires_at,
        )
        return {
            'token':      raw_token,
            'expires_at': invitation.expires_at,
            'role':       invitation.role,
            'area_id':    invitation.area_id,
        }


class AcceptInvitationSerializer(serializers.Serializer):
    token      = serializers.CharField()
    email      = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name  = serializers.CharField(max_length=150)
    password   = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        raw_token  = attrs['token']
        token_hash = Invitation.hash_token(raw_token)

        try:
            invitation = Invitation.objects.select_related('area').get(token_hash=token_hash)
        except Invitation.DoesNotExist:
            raise serializers.ValidationError({'token': 'Token de invitación inválido.'})

        if not invitation.is_valid:
            if invitation.used:
                raise serializers.ValidationError({'token': 'Esta invitación ya fue utilizada.'})
            raise serializers.ValidationError({'token': 'Esta invitación ha expirado.'})

        attrs['_invitation'] = invitation
        return attrs

    def save(self):
        invitation = self.validated_data['_invitation']
        email      = self.validated_data['email']
        first_name = self.validated_data['first_name']
        last_name  = self.validated_data['last_name']
        password   = self.validated_data['password']

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=invitation.role,
            area=invitation.area,
        )

        invitation.used = True
        invitation.save(update_fields=['used'])

        return user
