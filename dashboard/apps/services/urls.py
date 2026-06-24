from django.urls import path
from . import views

app_name = "services"

urlpatterns = [
    path("<slug:slug>/control/<str:action>/", views.ServiceControlView.as_view(), name="control"),
    path("<slug:slug>/status/", views.ServiceStatusView.as_view(), name="status"),
]
