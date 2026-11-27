from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from apps.keywords.services import owned_keywords
from apps.projects.services import owned_projects
from apps.scheduling.models import RankJob
from apps.scheduling.services import cancel_job, estimate_job, queue_job
from apps.scheduling.tasks import dispatch_pending

from .forms import KeywordLocationForm
from .indexing import IndexBatchForm, QuickIndexForm, queue_index_batch, queue_search_console_batch
from .models import IndexBatch, RankCheck
from .services import owned_configurations, save_configuration
from .tasks import dispatch_pending_index_checks


@login_required
def configuration_list(request):
    return render(request, "ranktracker/configurations.html", {"title": "Rank tracking", "configurations": owned_configurations(request.user)})


@login_required
def configuration_create(request, keyword_id):
    keyword = get_object_or_404(owned_keywords(request.user), pk=keyword_id)
    form = KeywordLocationForm(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        save_configuration(actor=request.user, keyword_id=keyword.id, form=form)
        messages.success(request, "Tracking configuration created.")
        return redirect("ranktracker:configurations")
    return render(request, "ranktracker/configuration_form.html", {"title": "Configure tracking", "keyword": keyword, "form": form})


@login_required
def job_preview(request, project_id):
    project = get_object_or_404(owned_projects(request.user), pk=project_id)
    try:
        estimate = estimate_job(actor=request.user, project=project)
    except ValidationError as exc:
        estimate = 0
        messages.error(request, "; ".join(exc.messages))
    if request.method == "POST" and estimate:
        try:
            job = queue_job(actor=request.user, project=project)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            if not getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
                try:
                    dispatch_pending.delay()
                except Exception:
                    messages.warning(request, "Job saved, but the task broker is unavailable. Start Redis/Celery or use the local processing command shown on the job page.")
            return redirect("ranktracker:job", job_id=job.id)
    return render(request, "ranktracker/job_preview.html", {"title": "Run rank check", "project": project, "estimate": estimate})


@login_required
def job_detail(request, job_id):
    job = get_object_or_404(RankJob.objects.filter(owner=request.user), pk=job_id)
    return render(request, "ranktracker/job_detail.html", {"title": "Rank check progress", "job": job})


@login_required
def job_cancel(request, job_id):
    if request.method == "POST":
        cancel_job(actor=request.user, job_id=job_id)
    return redirect("ranktracker:job", job_id=job_id)


@login_required
def history(request):
    queryset = RankCheck.objects.filter(configuration__keyword__project__owner=request.user).select_related("configuration__keyword", "configuration__location__country", "configuration__keyword__project")
    project_id = request.GET.get("project", "")
    if project_id.isdigit():
        queryset = queryset.filter(configuration__keyword__project_id=int(project_id))
    status = request.GET.get("status", "")
    if status in {"SUCCESS", "NOT_FOUND", "INCOMPLETE", "API_ERROR", "TIMEOUT", "INVALID_RESPONSE"}:
        queryset = queryset.filter(status=status)
    from django.utils.dateparse import parse_date

    start = parse_date(request.GET.get("start", ""))
    end = parse_date(request.GET.get("end", ""))
    if start:
        queryset = queryset.filter(created_at__date__gte=start)
    if end:
        queryset = queryset.filter(created_at__date__lte=end)
    page = Paginator(queryset, 50).get_page(request.GET.get("page"))
    return render(request, "ranktracker/history.html", {"title": "Ranking history", "page": page, "projects": owned_projects(request.user), "selected_project": project_id, "status": status, "statuses": ("SUCCESS", "NOT_FOUND", "INCOMPLETE", "API_ERROR", "TIMEOUT", "INVALID_RESPONSE"), "start": start, "end": end})


@login_required
def index_batches(request):
    batches = IndexBatch.objects.filter(owner=request.user).select_related("project")[:30]
    return render(request, "ranktracker/index_batches.html", {"title": "URL index checks", "batches": batches})


def _dispatch_index_batch(request):
    if not getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        try:
            dispatch_pending_index_checks.delay()
        except Exception:
            messages.warning(request, "Batch saved, but the task broker is unavailable. Run the local processing command shown on the report page.")


@login_required
def quick_index_create(request):
    form = QuickIndexForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            batch = queue_index_batch(actor=request.user, urls=form.cleaned_data["urls"])
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            _dispatch_index_batch(request)
            return redirect("ranktracker:index_batch", batch_id=batch.id)
    return render(request, "ranktracker/index_quick.html", {"title": "Quick URL search check", "form": form})


@login_required
def index_batch_create(request):
    form = IndexBatchForm(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            if form.cleaned_data["method"] == IndexBatch.Method.SEARCH_CONSOLE:
                batch = queue_search_console_batch(actor=request.user, project=form.cleaned_data["project"], grant=form.cleaned_data["gsc_property"], urls=form.cleaned_data["cleaned_urls"])
            else:
                batch = queue_index_batch(actor=request.user, project=form.cleaned_data["project"], location=form.cleaned_data["location"], urls=form.cleaned_data["cleaned_urls"])
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            _dispatch_index_batch(request)
            return redirect("ranktracker:index_batch", batch_id=batch.id)
    return render(request, "ranktracker/index_form.html", {"title": "Check URLs", "form": form})


@login_required
def index_batch_detail(request, batch_id):
    batch = get_object_or_404(IndexBatch.objects.filter(owner=request.user).select_related("project", "location"), pk=batch_id)
    return render(request, "ranktracker/index_batch.html", {"title": "URL index report", "batch": batch, "checks": batch.checks.all()})
