from django.urls import path
from . import views

app_name = "logs"

urlpatterns = [
    path("ekafy/", views.EkafyLogView.as_view(), name="ekafy"),
    path("<slug:slug>/", views.LogViewerView.as_view(), name="viewer"),
    path("<slug:slug>/stream/", views.LogStreamView.as_view(), name="stream"),
]
