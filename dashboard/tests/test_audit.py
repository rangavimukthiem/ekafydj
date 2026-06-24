"""
tests.audit — Unit tests for AuditService.
"""
import pytest
from apps.audit.models import AuditLog
from apps.audit.services import AuditService


@pytest.mark.django_db
class TestAuditService:

    def test_log_creates_record(self, admin_user):
        svc = AuditService()
        svc.log(
            user=admin_user,
            action="project.created",
            resource_type="project",
            resource_id="test-123",
            resource_name="My App",
            meta={"slug": "my-app"},
        )
        entry = AuditLog.objects.filter(action="project.created").first()
        assert entry is not None
        assert entry.username_snapshot == admin_user.username
        assert entry.resource_name == "My App"
        assert entry.meta["slug"] == "my-app"

    def test_log_does_not_raise_on_invalid_user(self):
        """Audit logging should never crash even with no user."""
        svc = AuditService()
        svc.log(action="system.startup", user=None)
        entry = AuditLog.objects.filter(action="system.startup").first()
        assert entry is not None
        assert entry.username_snapshot == "system"

    def test_audit_log_immutable(self, admin_user):
        svc = AuditService()
        svc.log(user=admin_user, action="test.action")
        entry = AuditLog.objects.first()
        entry.action = "modified.action"
        with pytest.raises(PermissionError):
            entry.save()
