from rest_framework import serializers
from apps.backups.models import Backup


class BackupSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    file_size_human = serializers.CharField(read_only=True)

    class Meta:
        model = Backup
        fields = [
            "id", "project", "project_name", "backup_type", "status",
            "file_name", "file_size", "file_size_human", "s3_url",
            "is_scheduled", "created_at",
        ]
        read_only_fields = fields
