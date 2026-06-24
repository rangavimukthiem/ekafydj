"""
api.viewsets — Monitoring ViewSet
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.monitoring.models import SystemMetric
from ..serializers.monitoring import SystemMetricSerializer


class SystemMetricViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SystemMetricSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = []
    ordering_fields = ["timestamp"]

    def get_queryset(self):
        return SystemMetric.objects.order_by("-timestamp")[:500]
