"""
tests — conftest.py
Shared pytest fixtures for the EKAFY test suite.
"""
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username="admin_test",
        email="admin@test.com",
        password="adminpass123!",
        role="admin",
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def operator_user(db):
    return User.objects.create_user(
        username="operator_test",
        email="operator@test.com",
        password="operatorpass123!",
        role="operator",
    )


@pytest.fixture
def viewer_user(db):
    return User.objects.create_user(
        username="viewer_test",
        email="viewer@test.com",
        password="viewerpass123!",
        role="viewer",
    )


@pytest.fixture
def project(db, admin_user):
    from apps.projects.models import Project
    return Project.objects.create(
        name="Test Project",
        slug="test-project",
        git_url="git@github.com:test/project.git",
        git_branch="main",
        db_name="ekafy_test_project",
        db_user="ekafy_test_project",
        db_password="testpass",
        status=Project.Status.ACTIVE,
        owner=admin_user,
    )


@pytest.fixture
def client_admin(client, admin_user):
    client.force_login(admin_user)
    return client


@pytest.fixture
def client_operator(client, operator_user):
    client.force_login(operator_user)
    return client


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def api_client_admin(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client
