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


class IndexBatch(TimestampedModel):
    class Method(models.TextChoices):
        SERPER = "SERPER", "Serper site search"
        SEARCH_CONSOLE = "GSC", "Google Search Console"

    owner = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="index_batches")
    project = models.ForeignKey("projects.Project", on_delete=models.PROTECT, related_name="index_batches", null=True, blank=True)
    location = models.ForeignKey("locations.Location", on_delete=models.PROTECT, null=True, blank=True)
    method = models.CharField(max_length=6, choices=Method.choices, default=Method.SERPER)
    site_url = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, default="PENDING")
    total = models.PositiveSmallIntegerField()
    completed = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("owner", "created_at"))]


class IndexCheck(TimestampedModel):
    batch = models.ForeignKey(IndexBatch, on_delete=models.PROTECT, related_name="checks")
    url = models.URLField(max_length=1000)
    status = models.CharField(max_length=30, default="PENDING")
    matched_url = models.URLField(max_length=1000, blank=True)
    verdict = models.CharField(max_length=30, blank=True)
    coverage_state = models.CharField(max_length=500, blank=True)
    google_canonical = models.URLField(max_length=1000, blank=True)
    last_crawl_time = models.DateTimeField(null=True, blank=True)
    request_identifier = models.UUIDField(null=True, blank=True, unique=True)
    error_message = models.CharField(max_length=500, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("url",)
        constraints = [models.UniqueConstraint(fields=("batch", "url"), name="index_batch_url_uniq")]
        indexes = [models.Index(fields=("status", "created_at"))]


class SearchConsoleGrant(TimestampedModel):
    """Admin-approved Search Console property for one project or account."""

    project = models.OneToOneField("projects.Project", on_delete=models.PROTECT, related_name="search_console_grant", null=True, blank=True)
    owner = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="search_console_grants", null=True, blank=True)
    site_url = models.CharField(max_length=500)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.CheckConstraint(
            condition=(models.Q(project__isnull=False, owner__isnull=True) | models.Q(project__isnull=True, owner__isnull=False)),
            name="gsc_grant_project_xor_owner",
        )]

    def clean(self):
        from .engine import domain_matches
        from .search_console import property_covers_url

        if bool(self.project_id) == bool(self.owner_id):
            raise ValidationError("Choose exactly one project or account for the Search Console grant.")
        if self.project_id:
            project = self.project
            if self.site_url.startswith("sc-domain:"):
                valid = property_covers_url(self.site_url, f"https://{project.root_domain}/")
            else:
                valid = property_covers_url(self.site_url, self.site_url) and domain_matches(
                    self.site_url, project.root_domain, project.match_subdomains
                )
            if not valid:
                raise ValidationError({"site_url": "Enter a Search Console property within this project's domain."})
        elif self.site_url.startswith("sc-domain:"):
            domain = self.site_url.removeprefix("sc-domain:")
            valid = property_covers_url(self.site_url, f"https://{domain}/") and not any(
                character in domain for character in "/?#@: "
            )
            if not valid:
                raise ValidationError({"site_url": "Enter a valid Search Console domain property."})
        elif not property_covers_url(self.site_url, self.site_url):
            raise ValidationError({"site_url": "Enter a URL-prefix property ending in / or a sc-domain property."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.site_url
