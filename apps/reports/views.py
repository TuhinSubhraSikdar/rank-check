from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.projects.services import owned_projects

from .models import Report
from .services import create_report, render_csv, render_html


@login_required
def report_list(request):
    reports = Report.objects.filter(owner=request.user).select_related("project")[:100]
    return render(request, "reports/list.html", {"title": "Reports", "reports": reports, "projects": owned_projects(request.user)})


@login_required
def generate(request, project_id):
    project = get_object_or_404(owned_projects(request.user), pk=project_id)
    if request.method != "POST":
        return redirect("reports:list")
    report = create_report(actor=request.user, project=project)
    return redirect("reports:preview", report_id=report.id)


@login_required
def preview(request, report_id):
    report = get_object_or_404(Report.objects.filter(owner=request.user), pk=report_id)
    return HttpResponse(render_html(report), content_type="text/html; charset=utf-8")


@login_required
def download(request, report_id, format):
    report = get_object_or_404(Report.objects.filter(owner=request.user), pk=report_id)
    if format == "html":
        response = HttpResponse(render_html(report), content_type="text/html; charset=utf-8")
    elif format == "csv":
        response = HttpResponse(render_csv(report), content_type="text/csv; charset=utf-8")
    else:
        return HttpResponse(status=404)
    response["Content-Disposition"] = f'attachment; filename="rank-report-{report.id}.{format}"'
    return response
