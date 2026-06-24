"""
apps.logs — Views
"""
import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views import View

from apps.projects.models import Project
from .services import LogService

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class LogViewerView(View):
    template_name = "logs/viewer.html"

    def get(self, request, slug):
        project = get_object_or_404(Project, slug=slug)
        svc = LogService()

        log_type = request.GET.get("type", "journal")
        lines = int(request.GET.get("lines", 200))
        search = request.GET.get("search", "")
        since = request.GET.get("since", "")

        if log_type == "journal":
            content = svc.get_journal_logs(
                project.systemd_service, lines=lines, search=search, since=since
            )
        elif log_type == "nginx_access":
            content = svc.get_nginx_access_log(project.slug, lines=lines)
        elif log_type == "nginx_error":
            content = svc.get_nginx_error_log(project.slug, lines=lines)
        else:
            content = svc.get_journal_logs(project.systemd_service, lines=lines)

        ctx = {
            "project": project,
            "log_content": content,
            "log_type": log_type,
            "lines": lines,
            "search": search,
            "since": since,
        }

        if request.htmx:
            return render(request, "logs/_log_content.html", ctx)
        return render(request, self.template_name, ctx)


@method_decorator(login_required, name="dispatch")
class LogStreamView(View):
    """SSE stream for live log tailing via journalctl -f."""

    def get(self, request, slug):
        project = get_object_or_404(Project, slug=slug)
        svc = LogService()

        def event_stream():
            for line in svc.stream_journal(project.systemd_service):
                yield f"data: {json.dumps({'line': line})}\n\n"

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


@method_decorator(login_required, name="dispatch")
class EkafyLogView(View):
    """View EKAFY dashboard's own logs."""
    template_name = "logs/ekafy_log.html"

    def get(self, request):
        svc = LogService()
        lines = int(request.GET.get("lines", 200))
        content = svc.get_ekafy_dashboard_log(lines=lines)
        return render(request, self.template_name, {"log_content": content, "lines": lines})
