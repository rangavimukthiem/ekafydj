"""
tests.deployments — Unit tests for DeploymentService.
"""
import pytest
from unittest.mock import patch, MagicMock

from apps.core.exceptions import DeploymentInProgressError
from apps.deployments.models import Deployment
from apps.deployments.services import DeploymentService


@pytest.mark.django_db
class TestDeploymentService:

    @patch("apps.deployments.services.run_deployment")
    def test_trigger_deployment_creates_record(self, mock_task, admin_user, project):
        mock_task.apply_async.return_value = MagicMock(id="task-123")

        svc = DeploymentService(acting_user=admin_user)
        deployment = svc.trigger_deployment(project)

        assert deployment.project == project
        assert deployment.status == Deployment.Status.PENDING
        assert deployment.triggered_by == admin_user

    @patch("apps.deployments.services.run_deployment")
    def test_trigger_raises_if_already_running(self, mock_task, admin_user, project):
        mock_task.apply_async.return_value = MagicMock(id="task-abc")

        # Create a running deployment
        Deployment.objects.create(
            project=project,
            status=Deployment.Status.RUNNING,
            git_branch="main",
        )

        svc = DeploymentService(acting_user=admin_user)
        with pytest.raises(DeploymentInProgressError):
            svc.trigger_deployment(project)

    def test_trigger_force_bypasses_running_check(self, admin_user, project):
        Deployment.objects.create(
            project=project,
            status=Deployment.Status.RUNNING,
            git_branch="main",
        )

        with patch("apps.deployments.services.run_deployment") as mock_task:
            mock_task.apply_async.return_value = MagicMock(id="task-forced")
            svc = DeploymentService(acting_user=admin_user)
            deployment = svc.trigger_deployment(project, force=True)
            assert deployment.status == Deployment.Status.PENDING
