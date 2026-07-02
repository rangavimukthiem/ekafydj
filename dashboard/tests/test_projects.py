"""
tests.projects — Unit tests for Project service and repository layers.
"""
import pytest
from unittest.mock import patch, MagicMock

from apps.core.exceptions import ProjectAlreadyExistsError
from apps.projects.models import Project
from apps.projects.repositories import ProjectRepository
from apps.projects.services import ProjectService


@pytest.mark.django_db
class TestProjectRepository:

    def test_get_all_returns_queryset(self, project):
        qs = ProjectRepository.get_all()
        assert project in qs

    def test_get_by_slug(self, project):
        found = ProjectRepository.get_by_slug(project.slug)
        assert found == project

    def test_get_by_slug_missing_returns_none(self):
        assert ProjectRepository.get_by_slug("nonexistent-slug") is None

    def test_exists_by_slug(self, project):
        assert ProjectRepository.exists_by_slug(project.slug) is True
        assert ProjectRepository.exists_by_slug("missing-slug") is False

    def test_update(self, project):
        updated = ProjectRepository.update(project, description="New description")
        assert updated.description == "New description"


@pytest.mark.django_db
class TestProjectService:

    @patch("apps.projects.services.run_privileged_script")
    def test_create_project_success(self, mock_script, admin_user):
        mock_script.return_value = MagicMock(returncode=0, stdout="")

        svc = ProjectService(acting_user=admin_user)
        project = svc.create_project(
            name="My New App",
            git_url="git@github.com:user/myapp.git",
        )

        assert project.name == "My New App"
        assert project.slug == "my-new-app"
        assert project.owner == admin_user
        assert project.db_password  # auto-generated
        assert project.secret_key   # auto-generated

    @patch("apps.projects.services.run_privileged_script")
    def test_create_project_duplicate_raises(self, mock_script, admin_user, project):
        svc = ProjectService(acting_user=admin_user)
        with pytest.raises(ProjectAlreadyExistsError):
            svc.create_project(
                name=project.name,
                git_url="git@github.com:user/other.git",
            )

    @patch("apps.projects.services.run_privileged_script")
    def test_archive_project(self, mock_script, admin_user, project):
        project.status = Project.Status.STOPPED
        project.save()

        svc = ProjectService(acting_user=admin_user)
        archived = svc.archive_project(project)
        assert archived.status == Project.Status.ARCHIVED

    def test_archive_active_project_raises(self, admin_user, project):
        project.status = Project.Status.ACTIVE
        project.save()
        svc = ProjectService(acting_user=admin_user)
        with pytest.raises(ValueError, match="Stop the project"):
            svc.archive_project(project)
