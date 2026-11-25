from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower

from apps.core.models import TimestampedModel


def normalize_domain(value: str) -> str:
    value = value.strip()
    parsed = urlsplit(value if "://" in value else f"https://{value}")
    host = (parsed.hostname or "").rstrip(".").lower()
    if not host or " " in host or "." not in host:
        raise ValidationError("Enter a valid public domain name.")
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ValidationError("Enter a valid domain name.") from exc
    return host[4:] if host.startswith("www.") else host


def normalize_website_url(value: str) -> str:
    value = value.strip()
    parsed = urlsplit(value if "://" in value else f"https://{value}")
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValidationError("Website URL must use HTTP or HTTPS.")
    host = normalize_domain(parsed.hostname or "")
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path.rstrip("/") or ""
    return urlunsplit((parsed.scheme.lower(), host + port, path, parsed.query, ""))


class Project(TimestampedModel):
    class Device(models.TextChoices):
        PROVIDER_DEFAULT = "DEFAULT", "Provider default"
        DESKTOP = "DESKTOP", "Desktop"
        MOBILE = "MOBILE", "Mobile"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=150)
    website_url = models.URLField(max_length=500)
    root_domain = models.CharField(max_length=253, blank=True)
    description = models.TextField(blank=True)
    country_code = models.CharField(max_length=2, blank=True)
    default_language = models.CharField(max_length=10, default="en")
    default_device = models.CharField(max_length=10, choices=Device.choices, default=Device.PROVIDER_DEFAULT)
    default_location = models.ForeignKey("locations.Location", on_delete=models.PROTECT, null=True, blank=True, related_name="default_for_projects")
    match_subdomains = models.BooleanField(default=True)
    time_zone = models.CharField(max_length=64, default="UTC")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name", "id")
        constraints = [models.UniqueConstraint(Lower("name"), "owner", name="project_owner_name_ci_uniq")]
        indexes = [models.Index(fields=("owner", "is_active"))]

    def clean(self):
        self.name = self.name.strip()
        self.website_url = normalize_website_url(self.website_url)
        self.root_domain = normalize_domain(self.root_domain or self.website_url)
        self.country_code = self.country_code.strip().upper()
        self.default_language = self.default_language.strip().lower()
        if self.default_location_id and self.owner_id:
            if self.default_location.owner_id != self.owner_id or not self.default_location.is_active:
                raise ValidationError({"default_location": "Choose an active location owned by this project owner."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
