"""
apps.deployments — Views
"""
import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView

from apps.core.exceptions import DeploymentInProgressError, DeploymentError
from apps.core.mixins import OperatorRequiredMixin
from apps.projects.models import Project

from .models import Deployment
from .repositories import DeploymentRepository
from .services import DeploymentService

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class DeploymentListView(ListView):
    model = Deployment
    template_name = "deployments/list.html"
    context_object_name = "deployments"
    paginate_by = 30

    def get_queryset(self):
        qs = DeploymentRepository.get_all()
        project_slug = self.request.GET.get("project")
        status = self.request.GET.get("status")
        if project_slug:
            qs = qs.filter(project__slug=project_slug)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Deployment.Status.choices
        ctx["projects"] = Project.objects.order_by("name")
        ctx["page_title"] = "Deployments"
        return ctx


@method_decorator(login_required, name="dispatch")
class DeploymentDetailView(View):
    template_name = "deployments/detail.html"

    def get(self, request, pk):
        deployment = get_object_or_404(
            Deployment.objects.select_related("project", "triggered_by"),
            pk=pk,
        )
        return render(request, self.template_name, {
            "deployment": deployment,
            "page_title": f"Deployments / {deployment.project.name}",
        })


@method_decorator(login_required, name="dispatch")
class TriggerDeploymentView(OperatorRequiredMixin, View):
    def post(self, request, slug):
        project = get_object_or_404(Project, slug=slug)
        try:
            svc = DeploymentService(acting_user=request.user)
            deployment = svc.trigger_deployment(project)
            messages.success(request, f"Deployment #{deployment.pk} triggered for '{project.name}'.")

            # HTMX: return partial or redirect
            if request.htmx:
                from django.template.response import TemplateResponse
                return TemplateResponse(
                    request,
                    "deployments/_status_badge.html",
                    {"deployment": deployment},
                )
            return redirect("deployments:detail", pk=deployment.pk)

        except DeploymentInProgressError as exc:
            messages.warning(request, str(exc))
        except DeploymentError as exc:
            messages.error(request, str(exc))

        return redirect("projects:detail", slug=slug)


@method_decorator(login_required, name="dispatch")
class DeploymentStatusView(View):
    """HTMX polling endpoint — returns badge partial for a deployment."""

    def get(self, request, pk):
        deployment = get_object_or_404(Deployment, pk=pk)
        if request.htmx:
            return render(request, "deployments/_status_badge.html", {"deployment": deployment})
        return JsonResponse({
            "status": deployment.status,
            "is_terminal": deployment.is_terminal,
        })


@method_decorator(login_required, name="dispatch")
class DeploymentLogStreamView(View):
    """
    SSE-style streaming endpoint for live log output.
    Returns chunked log lines while deployment is running.
    """

    def get(self, request, pk):
        deployment = get_object_or_404(Deployment, pk=pk)

        def event_stream():
            last_pos = 0
            import time
            for _ in range(300):  # max 5 min polling
                deployment.refresh_from_db(fields=["log", "status"])
                new_content = deployment.log[last_pos:]
                if new_content:
                    for line in new_content.splitlines():
                        yield f"data: {json.dumps({'line': line})}\n\n"
                    last_pos = len(deployment.log)
                if deployment.is_terminal:
                    yield f"data: {json.dumps({'done': True, 'status': deployment.status})}\n\n"
                    break
                time.sleep(1)

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


@method_decorator(login_required, name="dispatch")
class RollbackView(OperatorRequiredMixin, View):
    def post(self, request, pk):
        target = get_object_or_404(Deployment, pk=pk)
        project = target.project
        try:
            svc = DeploymentService(acting_user=request.user)
            rollback = svc.rollback(project, target)
            messages.warning(request, f"Rollback to commit {target.short_commit} triggered.")
            return redirect("deployments:detail", pk=rollback.pk)
        except DeploymentError as exc:
            messages.error(request, str(exc))
            return redirect("projects:detail", slug=project.slug)
