from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel


class RankJob(TimestampedModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    project = models.ForeignKey("projects.Project", on_delete=models.PROTECT)
    status = models.CharField(max_length=16, default="PENDING")
    total = models.PositiveIntegerField(default=0)
    completed = models.PositiveIntegerField(default=0)
    cancelled = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=("owner", "created_at"))]


class TrackingSchedule(TimestampedModel):
    class Frequency(models.TextChoices):
        DAILY = "DAILY", "Daily"
        THREE_DAYS = "THREE_DAYS", "Every three days"
        WEEKLY = "WEEKLY", "Weekly"
        MONTHLY = "MONTHLY", "Monthly"

    project = models.OneToOneField("projects.Project", on_delete=models.PROTECT, related_name="tracking_schedule")
    frequency = models.CharField(max_length=16, choices=Frequency.choices)
    next_run_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=("is_active", "next_run_at"))]
