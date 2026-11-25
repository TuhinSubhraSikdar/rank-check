from zoneinfo import ZoneInfo

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.projects.services import owned_projects

from .forms import TrackingScheduleForm
from .models import RankJob, TrackingSchedule
from .services import next_run


@login_required
def schedule_list(request):
    schedules = TrackingSchedule.objects.filter(project__owner=request.user).select_related("project")
    jobs = RankJob.objects.filter(owner=request.user).select_related("project")[:20]
    return render(request, "scheduling/list.html", {"title": "Schedules", "schedules": schedules, "jobs": jobs, "projects": owned_projects(request.user)})


@login_required
def schedule_edit(request, project_id):
    project = get_object_or_404(owned_projects(request.user), pk=project_id)
    schedule = TrackingSchedule.objects.filter(project=project).first()
    form = TrackingScheduleForm(request.POST or None, instance=schedule)
    if request.method == "POST" and form.is_valid():
        schedule = form.save(commit=False)
        schedule.project = project
        schedule.next_run_at = next_run(timezone.now().astimezone(ZoneInfo(project.time_zone)), schedule.frequency)
        schedule.save()
        messages.success(request, "Schedule saved.")
        return redirect("scheduling:list")
    return render(request, "scheduling/form.html", {"title": "Project schedule", "project": project, "form": form})
