import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.projects.services import owned_projects

from .forms import KeywordCSVForm, KeywordForm
from .services import archive_keyword, import_keywords, owned_keywords, safe_csv_cell, save_keyword


@login_required
def keyword_list(request, project_id):
    project = get_object_or_404(owned_projects(request.user), pk=project_id)
    queryset = owned_keywords(request.user, project=project)
    query = request.GET.get("q", "").strip()
    if query:
        queryset = queryset.filter(text__icontains=query)
    page = Paginator(queryset, 50).get_page(request.GET.get("page"))
    return render(request, "keywords/list.html", {"title": "Keywords", "project": project, "page": page, "query": query})


@login_required
def keyword_create(request, project_id):
    project = get_object_or_404(owned_projects(request.user), pk=project_id)
    form = KeywordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        save_keyword(actor=request.user, project=project, form=form)
        messages.success(request, "Keyword added.")
        return redirect("keywords:list", project_id=project.id)
    return render(request, "keywords/form.html", {"title": "Add keyword", "project": project, "form": form})


@login_required
def keyword_edit(request, project_id, pk):
    project = get_object_or_404(owned_projects(request.user), pk=project_id)
    keyword = get_object_or_404(owned_keywords(request.user, project=project), pk=pk)
    form = KeywordForm(request.POST or None, instance=keyword)
    if request.method == "POST" and form.is_valid():
        save_keyword(actor=request.user, project=project, form=form)
        messages.success(request, "Keyword updated.")
        return redirect("keywords:list", project_id=project.id)
    return render(request, "keywords/form.html", {"title": "Edit keyword", "project": project, "form": form})


@login_required
def keyword_archive(request, project_id, pk):
    project = get_object_or_404(owned_projects(request.user), pk=project_id)
    if request.method == "POST":
        get_object_or_404(owned_keywords(request.user, project=project), pk=pk)
        archive_keyword(actor=request.user, keyword_id=pk)
        messages.success(request, "Keyword archived.")
    return redirect("keywords:list", project_id=project.id)


@login_required
def keyword_import(request, project_id):
    project = get_object_or_404(owned_projects(request.user), pk=project_id)
    form = KeywordCSVForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            result = import_keywords(actor=request.user, project_id=project.id, upload=form.cleaned_data["file"])
        except ValidationError as exc:
            form.add_error("file", exc)
        else:
            messages.success(request, f"Imported {result.created} keywords; skipped {result.skipped} empty or duplicate rows.")
            return redirect("keywords:list", project_id=project.id)
    return render(request, "keywords/import.html", {"title": "Import keywords", "project": project, "form": form})


@login_required
def keyword_export(request, project_id):
    project = get_object_or_404(owned_projects(request.user), pk=project_id)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="project-{project.id}-keywords.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(("keyword", "target_url", "tags", "search_intent"))
    for keyword in owned_keywords(request.user, project=project).iterator(chunk_size=500):
        writer.writerow(tuple(safe_csv_cell(value) for value in (keyword.text, keyword.target_url, keyword.tags, keyword.search_intent)))
    return response


@login_required
def keyword_sample(request):
    response = HttpResponse("\ufeffkeyword,target_url,tags,search_intent\nseo agency,https://example.com/services,services,COMMERCIAL\n", content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="keyword-import-template.csv"'
    return response
