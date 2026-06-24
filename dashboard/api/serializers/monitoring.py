from rest_framework import serializers
from apps.monitoring.models import SystemMetric


class SystemMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemMetric
        fields = [
            "id", "timestamp", "cpu_percent", "memory_percent",
            "memory_used", "memory_total", "disk_percent", "disk_used",
            "disk_total", "load_avg_1", "load_avg_5", "load_avg_15",
        ]
        read_only_fields = fields
