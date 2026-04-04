from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from apps.areas.models import Area
from .models import Invitation

User = get_user_model()


class UserListSerializer(serializers.ModelSerializer):
    area_id   = serializers.UUIDField(read_only=True)
    area_name = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'area_id', 'area_name', 'created_at']
        read_only_fields = fields

    def get_area_name(self, obj):
        return obj.area.name if obj.area else None


class UserDetailSerializer(serializers.ModelSerializer):
    area_id   = serializers.UUIDField(read_only=True)
    area_name = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role',
            'area_id', 'area_name', 'biometrics_enabled', 'onboarding_completed',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'email', 'role', 'area_id', 'area_name',
            'biometrics_enabled', 'onboarding_completed',
            'created_at', 'updated_at',
        ]

    def get_area_name(self, obj):
        return obj.area.name if obj.area else None


class InvitationCreateSerializer(serializers.Serializer):
    area = serializers.PrimaryKeyRelatedField(
        queryset=Area.objects.all(),
        required=False,
        allow_null=True,
    )
    role = serializers.ChoiceField(
        choices=Invitation.Role.choices,
        default=Invitation.Role.TRABAJADOR,
    )

    def validate(self, attrs):
        role = attrs.get('role')
        area = attrs.get('area')
        if role == Invitation.Role.SUPER_ADMIN and area is not None:
            raise serializers.ValidationError(
                {'area': 'Las invitaciones de Super Admin no deben tener área.'}
            )
        if role in (Invitation.Role.ADMIN_AREA, Invitation.Role.TRABAJADOR) and area is None:
            raise serializers.ValidationError(
                {'area': 'Debes especificar un área para invitar a Admin de Área o Trabajador.'}
            )
        return attrs

    def save(self, created_by):
        area       = self.validated_data.get('area')
        role       = self.validated_data['role']
        raw_token, token_hash = Invitation.generate_token()
        code       = Invitation.generate_code()
        expires_at = timezone.now() + timedelta(hours=24)

        invitation = Invitation.objects.create(
            token_hash=token_hash,
            code=code,
            area=area,
            role=role,
            created_by=created_by,
            expires_at=expires_at,
        )
        return {
            'code':       invitation.code,
            'token':      raw_token,
            'expires_at': invitation.expires_at,
            'role':       invitation.role,
            'area_id':    str(invitation.area_id) if invitation.area_id else None,
        }


class VerifyInviteSerializer(serializers.Serializer):
    code = serializers.CharField()

    def validate(self, attrs):
        code = attrs['code'].strip()

        try:
            invitation = Invitation.objects.select_related('area').get(code=code)
        except Invitation.DoesNotExist:
            raise serializers.ValidationError({'code': 'Código inválido.'})

        if invitation.used:
            raise serializers.ValidationError({'code': 'Esta invitación ya fue utilizada.'})
        if not invitation.is_valid:
            raise serializers.ValidationError({'code': 'Esta invitación ha expirado.'})

        attrs['_invitation'] = invitation
        return attrs


class AcceptInvitationSerializer(serializers.Serializer):
    code       = serializers.CharField(required=False, allow_blank=True)
    token      = serializers.CharField(required=False, allow_blank=True)
    email      = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name  = serializers.CharField(max_length=150)
    password   = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Ya existe una cuenta con este correo.')
        return value

    def validate(self, attrs):
        code      = attrs.get('code', '').strip()
        raw_token = attrs.get('token', '').strip()

        if not code and not raw_token:
            raise serializers.ValidationError({'code': 'Debes proporcionar un código o token de invitación.'})

        invitation = None

        if code:
            try:
                invitation = Invitation.objects.select_related('area').get(code=code)
            except Invitation.DoesNotExist:
                pass

        if invitation is None and raw_token:
            token_hash = Invitation.hash_token(raw_token)
            try:
                invitation = Invitation.objects.select_related('area').get(token_hash=token_hash)
            except Invitation.DoesNotExist:
                pass

        if invitation is None:
            raise serializers.ValidationError({'code': 'Código de invitación inválido.'})

        if invitation.used:
            raise serializers.ValidationError({'code': 'Esta invitación ya fue utilizada.'})
        if not invitation.is_valid:
            raise serializers.ValidationError({'code': 'Esta invitación ha expirado.'})

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
