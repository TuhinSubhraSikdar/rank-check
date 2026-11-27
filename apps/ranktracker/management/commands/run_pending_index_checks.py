import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.ranktracker.models import IndexBatch, IndexCheck
from apps.ranktracker.tasks import run_index_check


class Command(BaseCommand):
    help = "Process previously confirmed pending URL index checks without Celery."

    def add_arguments(self, parser):
        parser.add_argument("--batch", type=int)
        parser.add_argument("--limit", type=int, default=25)
        parser.add_argument("--delay", type=float, default=2.0)

    def handle(self, *args, **options):
        if not 1 <= options["limit"] <= 100:
            raise CommandError("--limit must be between 1 and 100.")
        if options["delay"] < 0:
            raise CommandError("--delay cannot be negative.")
        checks = IndexCheck.objects.filter(status="PENDING", batch__status__in=("PENDING", "RUNNING"))
        if options["batch"]:
            checks = checks.filter(batch_id=options["batch"])
        ids = list(checks.order_by("created_at").values_list("id", flat=True)[:options["limit"]])
        if not ids:
            self.stdout.write("No confirmed pending URL checks found.")
            return
        methods = set(IndexCheck.objects.filter(pk__in=ids).values_list("batch__method", flat=True))
        if IndexBatch.Method.SERPER in methods and not settings.SERPER_API_KEY:
            raise CommandError("SERPER_API_KEY is not configured; no requests were sent.")
        if IndexBatch.Method.SEARCH_CONSOLE in methods and not settings.GSC_SERVICE_ACCOUNT_FILE:
            raise CommandError("GSC_SERVICE_ACCOUNT_FILE is not configured; no requests were sent.")
        self.stdout.write(f"Processing {len(ids)} confirmed URL checks.")
        for index, check_id in enumerate(ids):
            if index:
                time.sleep(options["delay"])
            if IndexCheck.objects.filter(pk=check_id, status="PENDING").update(status="QUEUED"):
                run_index_check(check_id)
                self.stdout.write(f"Check {check_id}: {IndexCheck.objects.get(pk=check_id).status}")
