from zoneinfo import ZoneInfo

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.ranktracker.engine import execute_check
from apps.ranktracker.models import RankCheck
from apps.serp_providers.serper import SerperProvider

from .models import RankJob, TrackingSchedule
from .services import next_run, queue_job


@shared_task(rate_limit=settings.RANK_RATE_LIMIT)
def run_check(check_id):
    check = RankCheck.objects.select_related("job").get(pk=check_id)
    if check.status != "QUEUED" or (check.job and check.job.cancelled):
        return
    try:
        execute_check(check_id=check_id, provider=SerperProvider())
    except Exception as exc:
        # The exception class is safe to retain; provider bodies and credentials are not.
        RankCheck.objects.filter(pk=check_id, status__in=("RUNNING", "QUEUED")).update(status="API_ERROR", error_message=f"Worker error: {type(exc).__name__}", completed_at=timezone.now())
    if check.job_id:
        job = RankJob.objects.get(pk=check.job_id)
        completed = job.checks.exclude(status__in=("PENDING", "QUEUED", "RUNNING")).count()
        job.completed = completed
        job.status = "CANCELLED" if job.cancelled else ("COMPLETED" if completed == job.total else "RUNNING")
        job.save(update_fields=("completed", "status", "updated_at"))


@shared_task
def dispatch_pending():
    ids = list(RankCheck.objects.filter(status="PENDING", job__cancelled=False).order_by("created_at").values_list("id", flat=True)[:settings.RANK_BATCH_SIZE])
    for check_id in ids:
        if RankCheck.objects.filter(pk=check_id, status="PENDING").update(status="QUEUED"):
            try:
                run_check.delay(check_id)
            except Exception:
                RankCheck.objects.filter(pk=check_id, status="QUEUED").update(status="PENDING")
                raise
    return len(ids)


@shared_task
def dispatch_due():
    due = TrackingSchedule.objects.filter(is_active=True, next_run_at__lte=timezone.now(), project__is_active=True).select_related("project__owner")[:settings.RANK_BATCH_SIZE]
    count = 0
    for schedule in due:
        with transaction.atomic():
            locked = TrackingSchedule.objects.select_for_update().get(pk=schedule.pk)
            if locked.next_run_at > timezone.now():
                continue
            try:
                queue_job(actor=locked.project.owner, project=locked.project)
            except Exception:
                # Leave due for operator attention; no silent billable retry loop.
                locked.is_active = False
                locked.save(update_fields=("is_active", "updated_at"))
                continue
            locked.next_run_at = next_run(locked.next_run_at.astimezone(ZoneInfo(locked.project.time_zone)), locked.frequency)
            locked.save(update_fields=("next_run_at", "updated_at"))
            count += 1
    return count
