from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ActivityAlert(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    title = models.CharField(max_length=160)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.INFO, db_index=True)
    dedupe_key = models.CharField(max_length=180, unique=True)
    target_url = models.CharField(max_length=240, blank=True)
    resolved = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="resolved_activity_alerts",
    )

    class Meta:
        ordering = ["resolved", "-created_at", "-id"]
        indexes = [
            models.Index(fields=["resolved", "severity", "created_at"], name="core_activi_resolve_4f00d2_idx"),
        ]

    def __str__(self):
        return self.title


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATED = "created", "Created"
        UPDATED = "updated", "Updated"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        CLOSED = "closed", "Closed"
        STOCK_USED = "stock_used", "Stock Used"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=30, choices=Action.choices, db_index=True)
    content_type = models.ForeignKey(
        "contenttypes.ContentType",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    object_id = models.PositiveBigIntegerField(blank=True, null=True)
    object_repr = models.CharField(max_length=220)
    details = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["action", "created_at"], name="core_auditl_action_29a2bf_idx"),
        ]

    def __str__(self):
        return f"{self.get_action_display()}: {self.object_repr}"
