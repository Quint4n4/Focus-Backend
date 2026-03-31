from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ['email']
    list_display = ['email', 'first_name', 'last_name', 'role', 'area', 'is_active', 'is_staff']
    list_filter  = ['role', 'is_active', 'is_staff', 'area']
    search_fields = ['email', 'first_name', 'last_name']

    fieldsets = (
        (None, {
            'fields': ('email', 'password'),
        }),
        (_('Información personal'), {
            'fields': ('first_name', 'last_name'),
        }),
        (_('Rol y área'), {
            'fields': ('role', 'area'),
        }),
        (_('Dispositivo y onboarding'), {
            'fields': ('biometrics_enabled', 'device_id', 'onboarding_completed'),
        }),
        (_('Permisos'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Fechas importantes'), {
            'fields': ('last_login',),
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2', 'role', 'area'),
        }),
    )
