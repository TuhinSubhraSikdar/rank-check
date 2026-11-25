from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.projects.services import owned_projects

from .forms import CompetitorForm
from .services import owned_competitors, save_competitor


@login_required
def competitor_list(request, project_id):
    project = get_object_or_404(owned_projects(request.user), pk=project_id)
    return render(request, "competitors/list.html", {"title": "Competitors", "project": project, "competitors": owned_competitors(request.user, project)})


@login_required
def competitor_create(request, project_id):
    project = get_object_or_404(owned_projects(request.user), pk=project_id)
    form = CompetitorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        save_competitor(actor=request.user, project=project, form=form)
        messages.success(request, "Competitor added.")
        return redirect("competitors:list", project_id=project.id)
    return render(request, "competitors/form.html", {"title": "Add competitor", "project": project, "form": form})


@login_required
def competitor_archive(request, project_id, pk):
    project = get_object_or_404(owned_projects(request.user), pk=project_id)
    competitor = get_object_or_404(owned_competitors(request.user, project), pk=pk)
    if request.method == "POST":
        competitor.is_active = False
        competitor.save(update_fields=("is_active", "updated_at"))
    return redirect("competitors:list", project_id=project.id)
