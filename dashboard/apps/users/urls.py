"""
apps.users — URL Patterns
"""
from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    path("", views.UserListView.as_view(), name="list"),
    path("invite/", views.InviteUserView.as_view(), name="invite"),
    path("<uuid:pk>/", views.UserDetailView.as_view(), name="detail"),
    path("<uuid:pk>/role/", views.ChangeRoleView.as_view(), name="change-role"),
    path("<uuid:pk>/toggle/", views.ToggleUserActiveView.as_view(), name="toggle-active"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
]
