from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .models import Company

User = get_user_model()


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Company
        fields = ['id', 'name', 'slug', 'is_active', 'created_at']
        read_only_fields = ['id', 'slug', 'is_active', 'created_at']


class CompanyRegistrationSerializer(serializers.Serializer):
    company_name     = serializers.CharField(max_length=200)
    company_slug     = serializers.SlugField(max_length=100, required=False, allow_blank=True)
    admin_email      = serializers.EmailField()
    admin_first_name = serializers.CharField(max_length=150)
    admin_last_name  = serializers.CharField(max_length=150)
    admin_password   = serializers.CharField(write_only=True, min_length=8)

    def validate_admin_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Ya existe una cuenta con este correo.')
        return value

    def validate(self, attrs):
        slug = attrs.get('company_slug', '').strip()
        if slug and Company.objects.filter(slug=slug).exists():
            raise serializers.ValidationError({'company_slug': 'Este slug ya está en uso.'})
        return attrs

    @transaction.atomic
    def save(self):
        data   = self.validated_data
        slug   = data.get('company_slug', '').strip() or Company.generate_slug(data['company_name'])

        company = Company.objects.create(
            name=data['company_name'],
            slug=slug,
        )
        user = User.objects.create_user(
            email=data['admin_email'],
            password=data['admin_password'],
            first_name=data['admin_first_name'],
            last_name=data['admin_last_name'],
            role='super_admin',
            company=company,
        )
        return company, user
