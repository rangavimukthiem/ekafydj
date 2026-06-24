"""
api.viewsets — Deployments ViewSet
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.deployments.models import Deployment
from apps.deployments.repositories import DeploymentRepository
from ..serializers.deployments import DeploymentSerializer


class DeploymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DeploymentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["status", "project"]
    ordering_fields = ["created_at", "status"]

    def get_queryset(self):
        return DeploymentRepository.get_all()
