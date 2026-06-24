from rest_framework import serializers
from apps.deployments.models import Deployment


class DeploymentSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    project_slug = serializers.CharField(source="project.slug", read_only=True)
    triggered_by_name = serializers.SerializerMethodField()
    duration_seconds = serializers.FloatField(read_only=True)
    short_commit = serializers.CharField(read_only=True)

    class Meta:
        model = Deployment
        fields = [
            "id", "project", "project_name", "project_slug",
            "status", "commit_hash", "short_commit", "commit_message",
            "commit_author", "git_branch", "triggered_by", "triggered_by_name",
            "started_at", "finished_at", "duration_seconds", "task_id",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_triggered_by_name(self, obj):
        return obj.triggered_by.display_name if obj.triggered_by else "System"
