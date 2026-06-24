"""
apps.projects — URL Patterns
"""
from django.urls import path
from . import views

app_name = "projects"

urlpatterns = [
    # Dashboard root → project overview
    path("", views.DashboardIndexView.as_view(), name="index"),

    # Project management
    path("list/", views.ProjectListView.as_view(), name="list"),
    path("new/", views.ProjectCreateView.as_view(), name="create"),
    path("<slug:slug>/", views.ProjectDetailView.as_view(), name="detail"),
    path("<slug:slug>/edit/", views.ProjectUpdateView.as_view(), name="edit"),
    path("<slug:slug>/archive/", views.ProjectArchiveView.as_view(), name="archive"),
    path("<slug:slug>/delete/", views.ProjectDeleteView.as_view(), name="delete"),
]
