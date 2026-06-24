"""
apps.backups — Views
"""
import logging
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView

from apps.core.mixins import OperatorRequiredMixin, AdminRequiredMixin
from apps.projects.models import Project

from .models import Backup, BackupSchedule
from .repositories import BackupRepository
from .services import BackupService

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class BackupListView(ListView):
    model = Backup
    template_name = "backups/list.html"
    context_object_name = "backups"
    paginate_by = 30

    def get_queryset(self):
        qs = BackupRepository.get_all()
        project_slug = self.request.GET.get("project")
        if project_slug:
            qs = qs.filter(project__slug=project_slug)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["projects"] = Project.objects.order_by("name")
        return ctx


@method_decorator(login_required, name="dispatch")
class TriggerBackupView(OperatorRequiredMixin, View):
    def post(self, request, slug):
        project = get_object_or_404(Project, slug=slug)
        backup_type = request.POST.get("backup_type", "db")

        svc = BackupService(acting_user=request.user)
        backup = svc.trigger_backup(project, backup_type=backup_type)

        messages.success(request, f"Backup triggered for '{project.name}'. Type: {backup.get_backup_type_display()}")
        return redirect("backups:list")


@method_decorator(login_required, name="dispatch")
class BackupDownloadView(View):
    def get(self, request, pk):
        backup = get_object_or_404(Backup, pk=pk, status=Backup.Status.SUCCESS)
        file_path = Path(backup.file_path)
        if not file_path.exists():
            messages.error(request, "Backup file not found on disk.")
            return redirect("backups:list")
        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=backup.file_name,
        )


@method_decorator(login_required, name="dispatch")
class BackupDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk):
        backup = get_object_or_404(Backup, pk=pk)
        svc = BackupService(acting_user=request.user)
        svc.delete_backup(backup)
        messages.warning(request, "Backup deleted.")
        return redirect("backups:list")
