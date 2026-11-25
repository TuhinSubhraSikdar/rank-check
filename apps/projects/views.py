from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProjectForm
from .services import archive_project, owned_projects, save_project


@login_required
def project_list(request):
    queryset = owned_projects(request.user)
    query = request.GET.get("q", "").strip()
    if query:
        queryset = queryset.filter(name__icontains=query)
    page = Paginator(queryset, 25).get_page(request.GET.get("page"))
    return render(request, "projects/list.html", {"title": "Projects", "page": page, "query": query})


@login_required
def project_create(request):
    form = ProjectForm(request.POST or None, actor=request.user)
    if request.method == "POST":
        project, form = save_project(actor=request.user, data=request.POST)
        if project:
            messages.success(request, "Project created.")
            return redirect("projects:detail", pk=project.pk)
    return render(request, "projects/form.html", {"title": "New project", "form": form})


@login_required
def project_detail(request, pk):
    project = get_object_or_404(owned_projects(request.user), pk=pk)
    return render(request, "projects/detail.html", {"title": project.name, "project": project})


@login_required
def project_edit(request, pk):
    project = get_object_or_404(owned_projects(request.user), pk=pk)
    form = ProjectForm(request.POST or None, instance=project, actor=request.user)
    if request.method == "POST":
        saved, form = save_project(actor=request.user, data=request.POST, instance=project)
        if saved:
            messages.success(request, "Project updated.")
            return redirect("projects:detail", pk=project.pk)
    return render(request, "projects/form.html", {"title": "Edit project", "form": form, "project": project})


@login_required
def project_archive(request, pk):
    if request.method != "POST":
        return redirect("projects:detail", pk=pk)
    get_object_or_404(owned_projects(request.user), pk=pk)
    archive_project(actor=request.user, project_id=pk)
    messages.success(request, "Project archived. Its history is preserved.")
    return redirect("projects:list")
