from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.ranktracker.models import KeywordLocation, RankCheck

from .models import RankJob


def eligible_configurations(project):
    return KeywordLocation.objects.filter(keyword__project=project, keyword__is_active=True, location__is_active=True, is_active=True, device="DEFAULT", requested_depth=10)


def estimate_job(*, actor, project):
    if project.owner_id != actor.id:
        raise PermissionDenied
    unsupported = KeywordLocation.objects.filter(keyword__project=project, is_active=True).exclude(device="DEFAULT", requested_depth=10).count()
    if unsupported:
        raise ValidationError("Project has unsupported device or depth configurations. Use provider-default Top 10.")
    return eligible_configurations(project).count()


@transaction.atomic
def queue_job(*, actor, project):
    from django.contrib.auth import get_user_model

    actor = get_user_model().objects.select_for_update().get(pk=actor.pk)
    if RankJob.objects.filter(owner=actor, project=project, cancelled=False, status__in=("PENDING", "RUNNING")).exists():
        raise ValidationError("A rank check job is already pending for this project. Process or cancel it before starting another.")
    count = estimate_job(actor=actor, project=project)
    if not count:
        raise ValidationError("Add an active provider-default Top 10 configuration first.")
    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    from apps.ranktracker.models import IndexBatch, IndexCheck
    from apps.usage.models import APIUsage

    used = APIUsage.objects.filter(user=actor, provider="serper", created_at__gte=month_start).count()
    pending = RankCheck.objects.filter(configuration__keyword__project__owner=actor, status__in=("PENDING", "QUEUED", "RUNNING")).count()
    pending += IndexCheck.objects.filter(batch__owner=actor, batch__method=IndexBatch.Method.SERPER, status__in=("PENDING", "QUEUED", "RUNNING")).count()
    from apps.ranktracker.models import IndexCheck

    pending_index = IndexCheck.objects.filter(batch__owner=actor, status__in=("PENDING", "QUEUED", "RUNNING")).count()
    if used + pending + pending_index + count > actor.monthly_request_quota:
        raise ValidationError("Monthly API request quota would be exceeded.")
    job = RankJob.objects.create(owner=actor, project=project, total=count)
    RankCheck.objects.bulk_create([RankCheck(job=job, configuration=config, requested_depth=10) for config in eligible_configurations(project).iterator(chunk_size=settings.RANK_BATCH_SIZE)])
    return job


@transaction.atomic
def cancel_job(*, actor, job_id):
    job = RankJob.objects.select_for_update().get(pk=job_id, owner=actor)
    job.cancelled = True
    job.status = "CANCELLED"
    job.save(update_fields=("cancelled", "status", "updated_at"))
    job.checks.filter(status__in=("PENDING", "QUEUED")).update(status="CANCELLED", completed_at=timezone.now())
    return job


def next_run(current, frequency):
    if frequency == "DAILY":
        return current + timedelta(days=1)
    if frequency == "THREE_DAYS":
        return current + timedelta(days=3)
    if frequency == "WEEKLY":
        return current + timedelta(days=7)
    if frequency == "MONTHLY":
        return current + relativedelta(months=1)
    raise ValidationError("Unsupported schedule frequency.")
