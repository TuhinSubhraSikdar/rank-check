from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.serp_providers.serper import SerperProvider

from .indexing import execute_index_check, execute_search_console_check
from .models import IndexBatch, IndexCheck
from .search_console import SearchConsoleClient


@shared_task(rate_limit=settings.RANK_RATE_LIMIT)
def run_index_check(check_id):
    try:
        check = IndexCheck.objects.select_related("batch").get(pk=check_id)
        if check.batch.method == IndexBatch.Method.SEARCH_CONSOLE:
            execute_search_console_check(check_id=check_id, client=SearchConsoleClient())
        else:
            execute_index_check(check_id=check_id, provider=SerperProvider())
    except Exception as exc:
        # Only an exception class is stored; provider responses and credentials stay private.
        check = IndexCheck.objects.select_related("batch").get(pk=check_id)
        if IndexCheck.objects.filter(pk=check_id, status__in=("RUNNING", "QUEUED")).update(
            status="API_ERROR", error_message=f"Worker error: {type(exc).__name__}", completed_at=timezone.now()
        ):
            batch = check.batch
            batch.completed = batch.checks.exclude(status__in=("PENDING", "QUEUED", "RUNNING")).count()
            batch.status = "COMPLETED" if batch.completed == batch.total else "RUNNING"
            batch.save(update_fields=("completed", "status", "updated_at"))


@shared_task
def dispatch_pending_index_checks():
    ids = list(IndexCheck.objects.filter(status="PENDING", batch__status__in=("PENDING", "RUNNING")).order_by("created_at").values_list("id", flat=True)[:settings.RANK_BATCH_SIZE])
    for check_id in ids:
        if IndexCheck.objects.filter(pk=check_id, status="PENDING").update(status="QUEUED"):
            try:
                run_index_check.delay(check_id)
            except Exception:
                IndexCheck.objects.filter(pk=check_id, status="QUEUED").update(status="PENDING")
                raise
    return len(ids)
