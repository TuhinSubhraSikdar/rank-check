from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from .models import APIUsage


@login_required
def usage_overview(request):
    queryset = APIUsage.objects.filter(user=request.user).select_related("project")
    summary = queryset.aggregate(total=Count("id"))
    by_project = queryset.values("project__name").annotate(requests=Count("id")).order_by("-requests")[:20]
    return render(request, "usage/overview.html", {"title": "API usage", "summary": summary, "by_project": by_project, "recent": queryset[:50], "quota": request.user.monthly_request_quota})
