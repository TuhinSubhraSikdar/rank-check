from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import dashboard_metrics


@login_required
def overview(request):
    return render(request, "dashboard/overview.html", {"title": "Overview", "metrics": dashboard_metrics(request.user)})
