"""
apps.core — Mixins
Reusable view and model mixins.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages


class AuditableMixin:
    """
    Model mixin for models that need audit log entries.
    Views using this mixin should call self.log_action().
    """

    def get_audit_resource_type(self) -> str:
        return self.__class__.__name__.lower()

    def get_audit_resource_id(self) -> str:
        return str(self.pk)


class ServiceMixin:
    """
    Mixin that provides a consistent way to call service layer methods
    and handle domain exceptions in views.
    """

    def handle_service_error(self, request, error, redirect_url=None):
        """Attach error message and redirect."""
        messages.error(request, str(error))
        from django.shortcuts import redirect
        return redirect(redirect_url or request.META.get("HTTP_REFERER", "/"))


class HtmxMixin:
    """Mixin to detect HTMX requests and return appropriate responses."""

    @property
    def is_htmx(self) -> bool:
        return getattr(self.request, "htmx", False)


class AdminRequiredMixin(LoginRequiredMixin):
    """Restrict view to admin-role users only."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role != "admin":
            messages.error(request, "Administrator access required.")
            from django.shortcuts import redirect
            return redirect("projects:index")
        return super().dispatch(request, *args, **kwargs)


class OperatorRequiredMixin(LoginRequiredMixin):
    """Restrict view to operator or admin role users."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in ("admin", "operator"):
            messages.error(request, "Operator or Administrator access required.")
            from django.shortcuts import redirect
            return redirect("projects:index")
        return super().dispatch(request, *args, **kwargs)
