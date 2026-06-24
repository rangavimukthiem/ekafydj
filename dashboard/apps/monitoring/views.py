"""
apps.monitoring — Views
"""
import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View

from .services import MonitoringService

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class MonitoringDashboardView(View):
    template_name = "monitoring/dashboard.html"

    def get(self, request):
        svc = MonitoringService()
        metric = svc.get_latest_metric()
        from apps.projects.models import Project
        projects = Project.objects.exclude(status="archived").select_related("owner")

        return render(request, self.template_name, {
            "metric": metric,
            "projects": projects,
        })


@method_decorator(login_required, name="dispatch")
class MetricsApiView(View):
    """JSON API for Chart.js time-series data."""

    def get(self, request):
        svc = MonitoringService()
        hours = int(request.GET.get("hours", 6))
        data = svc.get_metric_history(hours=hours)
        return JsonResponse({"metrics": data})


@method_decorator(login_required, name="dispatch")
class CurrentMetricsView(View):
    """HTMX polling endpoint — returns metric cards partial."""

    def get(self, request):
        svc = MonitoringService()
        metric = svc.get_latest_metric()
        if request.htmx:
            return render(request, "monitoring/_metric_cards.html", {"metric": metric})
        return JsonResponse(metric or {})
