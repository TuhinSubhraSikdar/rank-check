import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.ranktracker.models import RankCheck
from apps.scheduling.tasks import run_check


class Command(BaseCommand):
    help = "Process previously confirmed pending rank checks without a Celery broker."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=25)
        parser.add_argument("--project", type=int)
        parser.add_argument("--delay", type=float, default=2.0, help="Seconds between requests; default respects the 30/minute local rate.")

    def handle(self, *args, **options):
        if not settings.SERPER_API_KEY:
            raise CommandError("SERPER_API_KEY is not configured; no requests were sent.")
        limit = options["limit"]
        if not 1 <= limit <= 100:
            raise CommandError("--limit must be between 1 and 100.")
        if options["delay"] < 0:
            raise CommandError("--delay cannot be negative.")
        checks = RankCheck.objects.filter(status="PENDING", job__cancelled=False)
        if options["project"]:
            checks = checks.filter(configuration__keyword__project_id=options["project"])
        ids = list(checks.order_by("created_at").values_list("id", flat=True)[:limit])
        if not ids:
            self.stdout.write("No confirmed pending checks found.")
            return
        self.stdout.write(f"Processing {len(ids)} previously confirmed checks.")
        for index, check_id in enumerate(ids):
            if index:
                time.sleep(options["delay"])
            with transaction.atomic():
                claimed = RankCheck.objects.filter(pk=check_id, status="PENDING", job__cancelled=False).update(status="QUEUED")
            if claimed:
                run_check(check_id)
                check = RankCheck.objects.get(pk=check_id)
                self.stdout.write(f"Check {check_id}: {check.status}")
