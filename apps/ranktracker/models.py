from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.core.models import TimestampedModel
from apps.projects.models import Project


class KeywordLocation(TimestampedModel):
    class Source(models.TextChoices):
        MANUAL = "MANUAL", "Manual"
        PROJECT = "PROJECT", "Project location"

    keyword = models.ForeignKey("keywords.Keyword", on_delete=models.PROTECT, related_name="tracking_configurations")
    location = models.ForeignKey("locations.Location", on_delete=models.PROTECT, related_name="tracking_configurations")
    device = models.CharField(max_length=10, choices=Project.Device.choices, default=Project.Device.PROVIDER_DEFAULT)
    requested_depth = models.PositiveSmallIntegerField(default=10, choices=((10, "Top 10"), (50, "Top 50"), (100, "Top 100")))
    source = models.CharField(max_length=7, choices=Source.choices, default=Source.MANUAL)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("keyword", "location", "device"), name="keyword_location_device_uniq")]
        indexes = [models.Index(fields=("keyword", "is_active")), models.Index(fields=("location", "is_active"))]

    def clean(self):
        errors = {}
        if self.keyword_id and self.location_id:
            if self.keyword.project.owner_id != self.location.owner_id:
                errors["location"] = "Location and keyword project must have the same owner."
            if not self.keyword.is_active or not self.location.is_active:
                errors["is_active"] = "Archived keywords or locations cannot be tracked."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.keyword} · {self.location} · {self.get_device_display()}"


class RankCheck(TimestampedModel):
    job = models.ForeignKey("scheduling.RankJob", null=True, blank=True, on_delete=models.PROTECT, related_name="checks")
    configuration = models.ForeignKey(KeywordLocation, on_delete=models.PROTECT, related_name="checks")
    provider = models.CharField(max_length=50, default="serper")
    status = models.CharField(max_length=30, default="PENDING")
    requested_depth = models.PositiveSmallIntegerField()
    actual_checked_depth = models.PositiveSmallIntegerField(default=0)
    request_identifier = models.UUIDField(null=True, blank=True, unique=True)
    error_message = models.CharField(max_length=500, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("configuration", "created_at")), models.Index(fields=("status", "created_at"))]


class RankingResult(models.Model):
    rank_check = models.OneToOneField(RankCheck, on_delete=models.PROTECT, related_name="result")
    status = models.CharField(max_length=30)
    position = models.PositiveSmallIntegerField(null=True, blank=True)
    ranking_url = models.URLField(max_length=1000, blank=True)
    serp_title = models.CharField(max_length=500, blank=True)
    previous_position = models.PositiveSmallIntegerField(null=True, blank=True)
    movement = models.SmallIntegerField(null=True, blank=True)
    is_newly_ranked = models.BooleanField(default=False)
    checked_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ("-checked_at",)
        indexes = [models.Index(fields=("status", "checked_at")), models.Index(fields=("position", "checked_at"))]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Historical ranking results are immutable.")
        super().save(*args, **kwargs)
