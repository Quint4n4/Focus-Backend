from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, data):
        email    = data.get('email')
        password = data.get('password')

        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password,
            )
            if not user:
                # Respuesta genérica: no revelar si el email existe o no
                raise serializers.ValidationError(
                    'Credenciales inválidas.',
                    code='authorization',
                )
            if not user.is_active:
                raise serializers.ValidationError(
                    'La cuenta está desactivada.',
                    code='authorization',
                )
        else:
            raise serializers.ValidationError(
                'Debe proporcionar email y contraseña.',
                code='authorization',
            )

        data['user'] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    """Serializer de solo lectura para los datos del usuario autenticado."""

    area_id   = serializers.PrimaryKeyRelatedField(source='area', read_only=True)
    area_name = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'role',
            'area_id',
            'area_name',
            'biometrics_enabled',
            'onboarding_completed',
            'created_at',
        ]
        read_only_fields = fields

    def get_area_name(self, obj):
        return obj.area.name if obj.area else None


class BiometricEnableSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=255)

    def validate_device_id(self, value):
        if not value.strip():
            raise serializers.ValidationError('El device_id no puede estar vacío.')
        return value.strip()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
    )

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('La contraseña actual es incorrecta.')
        return value

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError(
                'La nueva contraseña debe tener al menos 8 caracteres.'
            )
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
