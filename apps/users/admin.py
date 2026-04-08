from django.contrib import admin

from .models import Invitation


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("code", "role", "area", "created_by", "used", "expires_at", "created_at")
    list_filter = ("role", "used", "expires_at", "created_at")
    search_fields = ("code", "created_by__email")
    readonly_fields = ("id", "token_hash", "code", "created_at")
