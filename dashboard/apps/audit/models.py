"""
apps.audit — Audit Log Model
Immutable record of every significant action on the platform.
"""
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    Immutable audit log. Never update, only insert.
    """

    # Who performed the action
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    username_snapshot = models.CharField(max_length=150, blank=True)  # snapshot at time of action

    # What was done
    action = models.CharField(max_length=100, db_index=True)  # e.g. "project.created"

    # What was affected
    resource_type = models.CharField(max_length=50, db_index=True)  # e.g. "project"
    resource_id = models.CharField(max_length=255, blank=True, db_index=True)
    resource_name = models.CharField(max_length=255, blank=True)

    # Where from
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    # Extra data (serialized)
    meta = models.JSONField(default=dict, blank=True)

    # When
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["resource_type", "resource_id"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.username_snapshot or 'system'}: {self.action}"

    def save(self, *args, **kwargs):
        """Prevent updates — audit logs are append-only."""
        if self.pk:
            raise PermissionError("Audit logs are immutable and cannot be updated.")
        if self.user and not self.username_snapshot:
            self.username_snapshot = self.user.username
        super().save(*args, **kwargs)
