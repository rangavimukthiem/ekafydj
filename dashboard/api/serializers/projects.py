from rest_framework import serializers
from apps.projects.models import Project


class ProjectSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "name", "slug", "description", "status", "status_display",
            "git_url", "git_branch", "domain", "python_version",
            "db_name", "systemd_service", "gunicorn_workers",
            "health_check_url", "is_healthy", "last_health_check",
            "owner", "owner_name", "tags", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at", "db_name", "systemd_service"]

    def get_owner_name(self, obj):
        return obj.owner.display_name if obj.owner else None


class ProjectCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, default="")
    git_url = serializers.CharField(max_length=500)
    git_branch = serializers.CharField(max_length=100, default="main")
    domain = serializers.CharField(max_length=253, required=False, default="")
    python_version = serializers.ChoiceField(choices=Project.PythonVersion.choices, default="3.12")
    gunicorn_workers = serializers.IntegerField(min_value=1, max_value=32, default=3)
    django_settings_module = serializers.CharField(max_length=200, default="config.settings.production")
