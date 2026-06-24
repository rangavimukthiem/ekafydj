"""
apps.services — Views
HTMX-powered start/stop/restart controls.
"""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from apps.core.exceptions import ServiceControlError
from apps.core.mixins import OperatorRequiredMixin
from apps.projects.models import Project

from .services import SystemdService

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class ServiceControlView(OperatorRequiredMixin, View):
    """
    POST endpoint to control systemd services.
    Supports HTMX — returns status badge partial on HTMX requests.
    """

    def post(self, request, slug, action):
        project = get_object_or_404(Project, slug=slug)
        svc = SystemdService(acting_user=request.user)

        try:
            if action == "start":
                svc.start(project)
                messages.success(request, f"'{project.name}' started.")
            elif action == "stop":
                svc.stop(project)
                messages.warning(request, f"'{project.name}' stopped.")
            elif action == "restart":
                svc.restart(project)
                messages.success(request, f"'{project.name}' restarted.")
            else:
                messages.error(request, f"Unknown action: {action}")
        except ServiceControlError as exc:
            messages.error(request, str(exc))

        if request.htmx:
            # Refresh project from DB and return updated badge
            project.refresh_from_db()
            return render(request, "services/_status_badge.html", {"project": project})

        return redirect("projects:detail", slug=slug)


@method_decorator(login_required, name="dispatch")
class ServiceStatusView(View):
    """Returns real-time systemd status for HTMX polling."""

    def get(self, request, slug):
        project = get_object_or_404(Project, slug=slug)
        svc = SystemdService()
        status = svc.get_status(project)

        if request.htmx:
            return render(request, "services/_status_badge.html", {
                "project": project,
                "systemd_status": status,
            })

        return HttpResponse(status["output"], content_type="text/plain")
