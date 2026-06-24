"""
api.viewsets — Backups ViewSet
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.backups.models import Backup
from apps.backups.repositories import BackupRepository
from apps.core.permissions import IsOperatorOrAdmin
from ..serializers.backups import BackupSerializer


class BackupViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BackupSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "backup_type", "project"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        return BackupRepository.get_all()

    @action(detail=False, methods=["post"], url_path="trigger",
            permission_classes=[IsOperatorOrAdmin])
    def trigger(self, request):
        from apps.projects.repositories import ProjectRepository
        from apps.backups.services import BackupService

        slug = request.data.get("project_slug")
        backup_type = request.data.get("backup_type", "db")

        if not slug:
            return Response({"error": "project_slug required"}, status=status.HTTP_400_BAD_REQUEST)

        project = ProjectRepository.get_by_slug(slug)
        if not project:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

        svc = BackupService(acting_user=request.user)
        backup = svc.trigger_backup(project, backup_type=backup_type)
        return Response(BackupSerializer(backup).data, status=status.HTTP_202_ACCEPTED)
