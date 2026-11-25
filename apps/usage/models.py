from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel


class APIUsage(TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="api_usage")
    project = models.ForeignKey("projects.Project", on_delete=models.PROTECT, related_name="api_usage")
    provider = models.CharField(max_length=50)
    request_identifier = models.UUIDField(unique=True)
    status = models.CharField(max_length=30)
    http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    requested_results = models.PositiveSmallIntegerField(default=10)
    actual_checked_depth = models.PositiveSmallIntegerField(default=0)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("user", "created_at")), models.Index(fields=("project", "created_at")), models.Index(fields=("provider", "created_at"))]
