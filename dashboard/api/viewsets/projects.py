"""
api.viewsets — Projects ViewSet
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import IsOperatorOrAdmin
from apps.projects.models import Project
from apps.projects.repositories import ProjectRepository
from apps.projects.services import ProjectService
from ..serializers.projects import ProjectSerializer, ProjectCreateSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"
    filterset_fields = ["status"]
    search_fields = ["name", "slug", "domain"]
    ordering_fields = ["name", "created_at", "status"]

    def get_queryset(self):
        return ProjectRepository.get_all()

    def get_serializer_class(self):
        if self.action == "create":
            return ProjectCreateSerializer
        return ProjectSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsOperatorOrAdmin()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = ProjectCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        svc = ProjectService(acting_user=request.user)
        project = svc.create_project(**serializer.validated_data)
        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsOperatorOrAdmin])
    def deploy(self, request, slug=None):
        """Trigger a deployment via the API."""
        project = self.get_object()
        from apps.deployments.services import DeploymentService
        from apps.deployments.models import Deployment
        svc = DeploymentService(acting_user=request.user)
        deployment = svc.trigger_deployment(project)
        return Response({"deployment_id": str(deployment.pk)}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["get"])
    def status(self, request, slug=None):
        """Get systemd service status."""
        project = self.get_object()
        from apps.services.services import SystemdService
        svc = SystemdService()
        return Response(svc.get_status(project))
