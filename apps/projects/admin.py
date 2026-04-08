from django.contrib import admin

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "area", "created_by", "target_date", "created_at")
    list_filter = ("status", "area", "target_date", "created_at")
    search_fields = ("name", "description", "created_by__email")
