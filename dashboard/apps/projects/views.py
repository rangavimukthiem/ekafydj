"""
apps.projects — Views
HTMX-compatible views for project management.
"""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, DetailView

from apps.core.mixins import OperatorRequiredMixin, AdminRequiredMixin, HtmxMixin
from apps.core.exceptions import ProjectAlreadyExistsError, ProjectError

from .forms import ProjectCreateForm, ProjectUpdateForm
from .models import Project
from .repositories import ProjectRepository
from .services import ProjectService

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class DashboardIndexView(View):
    """Main dashboard overview — project list + metrics summary."""
    template_name = "dashboard/index.html"

    def get(self, request):
        repo = ProjectRepository()
        projects = repo.get_all()
        return render(request, self.template_name, {
            "projects": projects,
            "active_count": projects.filter(status=Project.Status.ACTIVE).count(),
            "total_count": projects.count(),
            "failed_count": projects.filter(status=Project.Status.FAILED).count(),
        })


@method_decorator(login_required, name="dispatch")
class ProjectListView(ListView):
    model = Project
    template_name = "projects/list.html"
    context_object_name = "projects"
    paginate_by = 20

    def get_queryset(self):
        qs = ProjectRepository.get_all()
        q = self.request.GET.get("q", "")
        status = self.request.GET.get("status", "")
        if q:
            qs = qs.filter(name__icontains=q)
        if status:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = Project.Status.choices
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status_filter"] = self.request.GET.get("status", "")
        return ctx


@method_decorator(login_required, name="dispatch")
class ProjectDetailView(DetailView):
    model = Project
    template_name = "projects/detail.html"
    context_object_name = "project"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_object(self, queryset=None):
        return get_object_or_404(Project.objects.select_related("owner"), slug=self.kwargs["slug"])

    def get_context_data(self, **kwargs):
        from apps.deployments.models import Deployment
        from apps.backups.models import Backup
        ctx = super().get_context_data(**kwargs)
        ctx["recent_deployments"] = Deployment.objects.filter(
            project=self.object
        ).order_by("-created_at")[:5]
        ctx["recent_backups"] = Backup.objects.filter(
            project=self.object
        ).order_by("-created_at")[:5]
        return ctx


@method_decorator(login_required, name="dispatch")
class ProjectCreateView(OperatorRequiredMixin, View):
    template_name = "projects/create.html"

    def get(self, request):
        form = ProjectCreateForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = ProjectCreateForm(request.POST)
        if form.is_valid():
            try:
                svc = ProjectService(acting_user=request.user)
                project = svc.create_project(**form.cleaned_data)
                messages.success(request, f"Project '{project.name}' created successfully.")
                return redirect("projects:detail", slug=project.slug)
            except ProjectAlreadyExistsError as exc:
                messages.error(request, str(exc))
            except ProjectError as exc:
                messages.error(request, f"Project creation failed: {exc}")

        return render(request, self.template_name, {"form": form})


@method_decorator(login_required, name="dispatch")
class ProjectUpdateView(OperatorRequiredMixin, View):
    template_name = "projects/edit.html"

    def get(self, request, slug):
        project = get_object_or_404(Project, slug=slug)
        form = ProjectUpdateForm(instance=project)
        return render(request, self.template_name, {"form": form, "project": project})

    def post(self, request, slug):
        project = get_object_or_404(Project, slug=slug)
        form = ProjectUpdateForm(request.POST, instance=project)
        if form.is_valid():
            svc = ProjectService(acting_user=request.user)
            svc.update_project(project, **{
                k: v for k, v in form.cleaned_data.items()
            })
            messages.success(request, f"Project '{project.name}' updated.")
            return redirect("projects:detail", slug=project.slug)
        return render(request, self.template_name, {"form": form, "project": project})


@method_decorator(login_required, name="dispatch")
class ProjectArchiveView(AdminRequiredMixin, View):
    def post(self, request, slug):
        project = get_object_or_404(Project, slug=slug)
        try:
            svc = ProjectService(acting_user=request.user)
            svc.archive_project(project)
            messages.warning(request, f"Project '{project.name}' archived.")
        except (ProjectError, ValueError) as exc:
            messages.error(request, str(exc))
        return redirect("projects:list")


@method_decorator(login_required, name="dispatch")
class ProjectDeleteView(AdminRequiredMixin, View):
    def post(self, request, slug):
        project = get_object_or_404(Project, slug=slug)
        name = project.name
        svc = ProjectService(acting_user=request.user)
        svc.delete_project(project)
        messages.error(request, f"Project '{name}' permanently deleted from database.")
        return redirect("projects:list")
