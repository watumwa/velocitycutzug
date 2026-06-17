from django.contrib import admin

from .models import ActivityAlert, AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "object_repr")
    list_filter = ("action", "created_at")
    search_fields = ("object_repr", "actor__username", "actor__first_name", "actor__last_name")
    readonly_fields = ("actor", "action", "content_type", "object_id", "object_repr", "details", "created_at")


@admin.register(ActivityAlert)
class ActivityAlertAdmin(admin.ModelAdmin):
    list_display = ("created_at", "severity", "title", "resolved")
    list_filter = ("severity", "resolved", "created_at")
    search_fields = ("title", "message", "dedupe_key")
