from urllib.parse import urlsplit, urlunsplit
from uuid import UUID, uuid4

from django import forms
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.locations.services import owned_locations
from apps.projects.services import owned_projects
from apps.serp_providers.base import SearchStatus
from apps.usage.models import APIUsage

from .engine import domain_matches
from .models import IndexBatch, IndexCheck, RankCheck, SearchConsoleGrant
from .search_console import property_covers_url

MAX_INDEX_URLS = 25


def clean_index_url(value):
    value = value.strip()
    field = forms.URLField(max_length=1000, assume_scheme="https")
    try:
        value = field.clean(value)
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"http", "https"} or parsed.username or parsed.password or not parsed.hostname:
            raise ValueError
        host = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
        if parsed.port:
            host += f":{parsed.port}"
        path = parsed.path.rstrip("/") or "/"
        return urlunsplit((parsed.scheme.lower(), host, path, parsed.query, ""))
    except (ValueError, UnicodeError) as exc:
        raise ValidationError("Enter valid HTTP or HTTPS URLs without credentials.") from exc


class IndexBatchForm(forms.Form):
    method = forms.ChoiceField(choices=IndexBatch.Method.choices, initial=IndexBatch.Method.SERPER, required=False)
    project = forms.ModelChoiceField(queryset=None, required=False, empty_label="No project (standalone check)")
    location = forms.ModelChoiceField(queryset=None, required=False, help_text="Optional for a standalone Serper check. Without one, the search uses US/English settings.")
    gsc_property = forms.ModelChoiceField(queryset=None, required=False, label="Search Console property", help_text="Required for a Search Console check without a project. An administrator must approve it for your account.")
    urls = forms.CharField(widget=forms.Textarea(attrs={"rows": 12, "placeholder": "https://example.com/page-one\nhttps://example.com/page-two"}), help_text=f"One URL per line, up to {MAX_INDEX_URLS}. Duplicates are removed and URLs are sorted.")

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = owned_projects(actor)
        self.fields["location"].queryset = owned_locations(actor)
        self.fields["gsc_property"].queryset = SearchConsoleGrant.objects.filter(owner=actor, project__isnull=True, is_active=True)

    def clean_method(self):
        return self.cleaned_data["method"] or IndexBatch.Method.SERPER

    def clean(self):
        cleaned = super().clean()
        project = cleaned.get("project")
        grant = cleaned.get("gsc_property")
        raw = cleaned.get("urls")
        if not raw:
            return cleaned
        method = cleaned.get("method")
        if method == IndexBatch.Method.SERPER:
            if project and (not project.default_location or not project.default_location.is_active):
                self.add_error("project", "Choose an active default location for Serper checks.")
        if method == IndexBatch.Method.SEARCH_CONSOLE:
            if not settings.GSC_SERVICE_ACCOUNT_FILE:
                self.add_error("method", "Search Console credentials are not configured by the administrator.")
            elif project and not SearchConsoleGrant.objects.filter(project=project, is_active=True).exists():
                self.add_error("project", "Ask an administrator to approve a Search Console property for this project.")
            elif not project and not grant:
                self.add_error("gsc_property", "Choose an administrator-approved Search Console property.")
        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if len(lines) > MAX_INDEX_URLS:
            self.add_error("urls", f"Enter no more than {MAX_INDEX_URLS} URLs.")
            return cleaned
        urls = []
        for number, line in enumerate(lines, start=1):
            try:
                url = clean_index_url(line)
            except ValidationError:
                self.add_error("urls", f"Line {number} is not a valid URL.")
                continue
            if project and not domain_matches(url, project.root_domain, project.match_subdomains):
                self.add_error("urls", f"Line {number} is outside the selected project domain.")
                continue
            urls.append(url)
        if not urls and not self.errors:
            self.add_error("urls", "Enter at least one URL.")
        cleaned["cleaned_urls"] = sorted(set(urls))
        if method == IndexBatch.Method.SEARCH_CONSOLE:
            if project:
                grant = SearchConsoleGrant.objects.filter(project=project, is_active=True).first()
            if grant and any(not property_covers_url(grant.site_url, url) for url in cleaned["cleaned_urls"]):
                self.add_error("urls", "Every URL must be within the approved Search Console property.")
        return cleaned


class QuickIndexForm(forms.Form):
    urls = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 12, "placeholder": "https://example.com/page-one\nhttps://example.com/page-two"}),
        help_text=f"One URL per line, up to {MAX_INDEX_URLS}. Duplicates are removed.",
    )

    def clean_urls(self):
        lines = [line.strip() for line in self.cleaned_data["urls"].splitlines() if line.strip()]
        if not lines:
            raise ValidationError("Enter at least one URL.")
        if len(lines) > MAX_INDEX_URLS:
            raise ValidationError(f"Enter no more than {MAX_INDEX_URLS} URLs.")
        urls = []
        for number, line in enumerate(lines, start=1):
            try:
                urls.append(clean_index_url(line))
            except ValidationError as exc:
                raise ValidationError(f"Line {number} is not a valid URL.") from exc
        return sorted(set(urls))


@transaction.atomic
def queue_index_batch(*, actor, urls, project=None, location=None):
    if not settings.SERPER_API_KEY:
        raise ValidationError("Serper API key is not configured.")
    if project is not None:
        if project.owner_id != actor.id or not project.is_active:
            raise PermissionDenied
        location = project.default_location
    if project is not None and location is None:
        raise ValidationError("Choose an active project location first.")
    if location and (location.owner_id != actor.id or not location.is_active or not location.country.is_active):
        raise ValidationError("Choose an active location owned by your account.")
    if not urls or len(urls) > MAX_INDEX_URLS or len(urls) != len(set(urls)):
        raise ValidationError("Enter 1 to 25 unique URLs.")
    if any(clean_index_url(url) != url or (project and not domain_matches(url, project.root_domain, project.match_subdomains)) for url in urls):
        raise ValidationError("URLs must be cleaned and, when a project is selected, belong to it.")
    from django.contrib.auth import get_user_model

    locked_actor = get_user_model().objects.select_for_update().get(pk=actor.pk)
    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = APIUsage.objects.filter(user=locked_actor, provider="serper", created_at__gte=month_start).count()
    pending_ranks = RankCheck.objects.filter(configuration__keyword__project__owner=locked_actor, status__in=("PENDING", "QUEUED", "RUNNING")).count()
    pending_index = IndexCheck.objects.filter(batch__owner=locked_actor, batch__method=IndexBatch.Method.SERPER, status__in=("PENDING", "QUEUED", "RUNNING")).count()
    if used + pending_ranks + pending_index + len(urls) > locked_actor.monthly_request_quota:
        raise ValidationError("Monthly API request quota would be exceeded.")
    batch = IndexBatch.objects.create(owner=locked_actor, project=project, location=location, total=len(urls))
    IndexCheck.objects.bulk_create([IndexCheck(batch=batch, url=url) for url in urls])
    return batch


@transaction.atomic
def queue_search_console_batch(*, actor, urls, project=None, grant=None):
    if project is not None and (project.owner_id != actor.id or not project.is_active):
        raise PermissionDenied
    if not settings.GSC_SERVICE_ACCOUNT_FILE:
        raise ValidationError("Search Console credentials are not configured.")
    if project is not None:
        grant = SearchConsoleGrant.objects.filter(project=project, is_active=True).first()
    else:
        if grant is not None and grant.owner_id != actor.id:
            raise PermissionDenied
        grant = SearchConsoleGrant.objects.filter(pk=getattr(grant, "pk", None), owner=actor, project__isnull=True, is_active=True).first()
    if grant is None:
        raise ValidationError("No approved Search Console property is available for this check.")
    if not urls or len(urls) > MAX_INDEX_URLS or len(urls) != len(set(urls)):
        raise ValidationError("Enter 1 to 25 unique URLs.")
    if any(
        clean_index_url(url) != url
        or (project and not domain_matches(url, project.root_domain, project.match_subdomains))
        or not property_covers_url(grant.site_url, url)
        for url in urls
    ):
        raise ValidationError("URLs must belong to the approved Search Console property and any selected project.")
    day_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    property_checks = IndexCheck.objects.filter(batch__site_url=grant.site_url, batch__method=IndexBatch.Method.SEARCH_CONSOLE)
    used = property_checks.filter(completed_at__gte=day_start).count()
    pending = property_checks.filter(status__in=("PENDING", "QUEUED", "RUNNING")).count()
    if used + pending + len(urls) > settings.GSC_DAILY_PROPERTY_LIMIT:
        raise ValidationError("The configured daily Search Console property limit would be exceeded.")
    batch = IndexBatch.objects.create(
        owner=actor, project=project, method=IndexBatch.Method.SEARCH_CONSOLE,
        site_url=grant.site_url, total=len(urls),
    )
    IndexCheck.objects.bulk_create([IndexCheck(batch=batch, url=url) for url in urls])
    return batch


def execute_search_console_check(*, check_id, client):
    with transaction.atomic():
        check = IndexCheck.objects.select_for_update().select_related("batch__project").get(pk=check_id)
        if check.batch.method != IndexBatch.Method.SEARCH_CONSOLE or check.status not in {"PENDING", "QUEUED"}:
            return check
        batch = check.batch
        if batch.project_id:
            permitted = batch.project.owner_id == batch.owner_id and SearchConsoleGrant.objects.filter(
                project_id=batch.project_id, site_url=batch.site_url, is_active=True
            ).exists()
        else:
            permitted = SearchConsoleGrant.objects.filter(
                owner_id=batch.owner_id, project__isnull=True, site_url=batch.site_url, is_active=True
            ).exists()
        if not permitted:
            return _cancel_index_check(check)
        check.status = "RUNNING"
        check.save(update_fields=("status", "updated_at"))
    batch = check.batch
    inspection = client.inspect(url=check.url, site_url=batch.site_url)
    with transaction.atomic():
        check = IndexCheck.objects.select_for_update().get(pk=check_id)
        request_id = uuid4()
        APIUsage.objects.create(
            user=batch.owner, project=batch.project, provider=client.name,
            request_identifier=request_id, status=inspection.status,
            http_status=inspection.http_status, requested_results=1,
        )
        check.request_identifier = request_id
        check.status = inspection.status
        check.verdict = inspection.verdict
        check.coverage_state = inspection.coverage_state
        check.google_canonical = inspection.google_canonical
        if inspection.last_crawl_time:
            from django.utils.dateparse import parse_datetime

            check.last_crawl_time = parse_datetime(inspection.last_crawl_time)
        check.completed_at = timezone.now()
        check.save(update_fields=(
            "request_identifier", "status", "verdict", "coverage_state",
            "google_canonical", "last_crawl_time", "completed_at", "updated_at",
        ))
        batch.completed = batch.checks.exclude(status__in=("PENDING", "QUEUED", "RUNNING")).count()
        batch.status = "COMPLETED" if batch.completed == batch.total else "RUNNING"
        batch.save(update_fields=("completed", "status", "updated_at"))
    return check


def execute_index_check(*, check_id, provider):
    with transaction.atomic():
        check = IndexCheck.objects.select_for_update().select_related("batch__project", "batch__location__country").get(pk=check_id)
        if check.status not in {"PENDING", "QUEUED"} or check.batch.status == "CANCELLED":
            return check
        batch = check.batch
        invalid_location = batch.location and (
            batch.location.owner_id != batch.owner_id
            or not batch.location.is_active
            or not batch.location.country.is_active
        )
        if (
            batch.method != IndexBatch.Method.SERPER
            or invalid_location
            or (batch.project_id and (batch.project.owner_id != batch.owner_id or not batch.project.is_active))
            or (batch.project_id and batch.location is None)
        ):
            return _cancel_index_check(check)
        check.status = "RUNNING"
        check.save(update_fields=("status", "updated_at"))
    batch = check.batch
    language = batch.project.default_language if batch.project_id else (batch.location.language_code if batch.location else "en")
    result = provider.search(keyword=f"site:{check.url}", location=batch.location, language=language, device="DEFAULT", depth=10)
    with transaction.atomic():
        check = IndexCheck.objects.select_for_update().get(pk=check_id)
        metadata = result.request_metadata
        request_id = UUID(metadata["request_id"])
        APIUsage.objects.create(user=batch.owner, project=batch.project, provider=provider.name, request_identifier=request_id, status=result.status.value, http_status=metadata.get("http_status"), requested_results=metadata.get("requested_results", 10), actual_checked_depth=result.actual_checked_depth, duration_ms=metadata.get("duration_ms"))
        check.request_identifier = request_id
        check.completed_at = timezone.now()
        check.error_message = result.error_message[:500]
        if result.status in {SearchStatus.SUCCESS, SearchStatus.INCOMPLETE}:
            matches = []
            for item in result.organic_results:
                try:
                    if clean_index_url(item.link) == check.url:
                        matches.append(item)
                except ValidationError:
                    continue
            check.status = "FOUND" if matches else "NOT_CONFIRMED"
            check.matched_url = min(matches, key=lambda item: item.position).link[:1000] if matches else ""
        else:
            check.status = result.status.value
        check.save(update_fields=("request_identifier", "completed_at", "error_message", "status", "matched_url", "updated_at"))
        batch.completed = batch.checks.exclude(status__in=("PENDING", "QUEUED", "RUNNING")).count()
        batch.status = "COMPLETED" if batch.completed == batch.total else "RUNNING"
        batch.save(update_fields=("completed", "status", "updated_at"))
    return check


def _cancel_index_check(check):
    """Cancel an unstarted attempt whose owner context is no longer valid."""
    check.status = "CANCELLED"
    check.completed_at = timezone.now()
    check.save(update_fields=("status", "completed_at", "updated_at"))
    batch = check.batch
    batch.completed = batch.checks.exclude(status__in=("PENDING", "QUEUED", "RUNNING")).count()
    batch.status = "COMPLETED" if batch.completed == batch.total else "RUNNING"
    batch.save(update_fields=("completed", "status", "updated_at"))
    return check
