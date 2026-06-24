from django.urls import path
from . import views

app_name = "backups"

urlpatterns = [
    path("", views.BackupListView.as_view(), name="list"),
    path("trigger/<slug:slug>/", views.TriggerBackupView.as_view(), name="trigger"),
    path("<uuid:pk>/download/", views.BackupDownloadView.as_view(), name="download"),
    path("<uuid:pk>/delete/", views.BackupDeleteView.as_view(), name="delete"),
]
