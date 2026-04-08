from django.contrib import admin

from .models import Area


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "created_at", "updated_at")
    search_fields = ("name", "description", "created_by__email")
    list_filter = ("created_at", "updated_at")
