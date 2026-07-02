"""
apps.audit — Views
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.contrib.auth import get_user_model

from .models import AuditLog

User = get_user_model()


class AuditLogListView(LoginRequiredMixin, ListView):
    model = AuditLog
    template_name = "audit/list.html"
    context_object_name = "audit_logs"
    paginate_by = 50

    def get_queryset(self):
        qs = AuditLog.objects.select_related("user").order_by("-created_at")

        # Filters
        action = self.request.GET.get("action")
        resource_type = self.request.GET.get("resource_type")
        user_id = self.request.GET.get("user")

        if action:
            qs = qs.filter(action__icontains=action)
        if resource_type:
            qs = qs.filter(resource_type=resource_type)
        if user_id:
            qs = qs.filter(user_id=user_id)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["users"] = User.objects.filter(is_active=True).order_by("username")
        ctx["action_filter"] = self.request.GET.get("action", "")
        ctx["resource_filter"] = self.request.GET.get("resource_type", "")
        ctx["page_title"] = "Audit Log"
        return ctx
