from django.contrib import admin

from .models import Activity, ActivityAttachment, ActivityLog


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "owner", "assigned_to", "area", "project", "target_date", "created_at")
    list_filter = ("status", "area", "project", "target_date", "created_at")
    search_fields = ("title", "description", "owner__email", "assigned_to__email")


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("activity", "event_type", "user", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("activity__title", "user__email")


@admin.register(ActivityAttachment)
class ActivityAttachmentAdmin(admin.ModelAdmin):
    list_display = ("activity", "uploaded_by", "created_at")
    list_filter = ("created_at",)
    search_fields = ("activity__title", "uploaded_by__email")
