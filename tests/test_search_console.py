from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.locations.models import Country, Location
from apps.projects.models import Project
from apps.ranktracker.indexing import (
    IndexBatchForm,
    execute_search_console_check,
    queue_index_batch,
    queue_search_console_batch,
)
from apps.ranktracker.models import SearchConsoleGrant
from apps.ranktracker.search_console import SearchConsoleClient, property_covers_url
from apps.usage.models import APIUsage

pytestmark = pytest.mark.django_db


@pytest.fixture
def approved_project():
    owner = User.objects.create_user("owner", "owner@example.com", "safe-password-123")
    project = Project.objects.create(owner=owner, name="Site", website_url="https://example.com")
    SearchConsoleGrant.objects.create(project=project, site_url="sc-domain:example.com")
    return project


def test_property_boundary_and_admin_grant_validation(approved_project):
    assert property_covers_url("sc-domain:example.com", "https://shop.example.com/a")
    assert not property_covers_url("sc-domain:example.com", "https://example.com.evil.test/a")
    assert property_covers_url("https://example.com/blog/", "https://example.com/blog/a")
    assert not property_covers_url("https://example.com/blog/", "https://example.com/blogger/a")
    with pytest.raises(ValidationError):
        SearchConsoleGrant.objects.create(project=Project.objects.create(
            owner=approved_project.owner, name="Other", website_url="https://other.test"
        ), site_url="sc-domain:example.com")


@override_settings(GSC_SERVICE_ACCOUNT_FILE="")
def test_gsc_form_requires_admin_credentials(approved_project):
    form = IndexBatchForm(data={
        "method": "GSC", "project": approved_project.pk,
        "urls": "https://example.com/a",
    }, actor=approved_project.owner)
    assert not form.is_valid()
    assert "credentials" in str(form.errors).lower()


@override_settings(GSC_SERVICE_ACCOUNT_FILE="/private/service-account.json")
def test_gsc_form_and_queue_require_owned_approved_property(approved_project, client):
    owner = approved_project.owner
    outsider = User.objects.create_user("outsider", "outsider@example.com", "safe-password-123")
    form = IndexBatchForm(data={
        "method": "GSC", "project": approved_project.pk,
        "urls": "https://example.com/b\nhttps://example.com/a",
    }, actor=owner)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["cleaned_urls"] == ["https://example.com/a", "https://example.com/b"]
    assert not IndexBatchForm(data={
        "method": "GSC", "project": approved_project.pk,
        "urls": "https://example.com/a",
    }, actor=outsider).is_valid()
    with pytest.raises(PermissionDenied):
        queue_search_console_batch(actor=outsider, project=approved_project, urls=["https://example.com/a"])
    batch = queue_search_console_batch(actor=owner, project=approved_project, urls=form.cleaned_data["cleaned_urls"])
    assert batch.method == "GSC"
    assert batch.site_url == "sc-domain:example.com"
    assert batch.location is None
    client.force_login(outsider)
    assert client.get(reverse("ranktracker:index_batch", args=[batch.pk])).status_code == 404
    client.force_login(owner)
    response = client.get(reverse("ranktracker:index_batch", args=[batch.pk]))
    assert response.status_code == 200
    assert b"Google Search Console" in response.content


@override_settings(GSC_SERVICE_ACCOUNT_FILE="/private/service-account.json")
def test_gsc_paste_flow_queues_without_calling_google(approved_project, client):
    client.force_login(approved_project.owner)
    with patch("apps.ranktracker.search_console.requests.post") as post:
        response = client.post(reverse("ranktracker:index_new"), {
            "method": "GSC", "project": approved_project.pk,
            "urls": "https://example.com/b\nhttps://example.com/a",
        })
    assert response.status_code == 302
    assert approved_project.index_batches.get().method == "GSC"
    post.assert_not_called()


@override_settings(GSC_SERVICE_ACCOUNT_FILE="/private/service-account.json")
def test_standalone_gsc_uses_account_grant_and_preserves_tenant_isolation(approved_project, client):
    owner = approved_project.owner
    outsider = User.objects.create_user("outsider", "outsider@example.com", "safe-password-123")
    grant = SearchConsoleGrant.objects.create(owner=owner, site_url="sc-domain:example.com")
    form = IndexBatchForm(data={
        "method": "GSC", "gsc_property": grant.pk,
        "urls": "https://shop.example.com/page",
    }, actor=owner)
    assert form.is_valid(), form.errors
    assert not IndexBatchForm(data={
        "method": "GSC", "gsc_property": grant.pk,
        "urls": "https://shop.example.com/page",
    }, actor=outsider).is_valid()
    with pytest.raises(PermissionDenied):
        queue_search_console_batch(actor=outsider, grant=grant, urls=["https://shop.example.com/page"])
    with pytest.raises(ValidationError):
        queue_search_console_batch(actor=owner, grant=grant, urls=["https://example.com.evil.test/page"])
    client.force_login(owner)
    response = client.post(reverse("ranktracker:index_new"), {
        "method": "GSC", "gsc_property": grant.pk,
        "urls": "https://shop.example.com/page",
    })
    assert response.status_code == 302
    batch = owner.index_batches.get(project__isnull=True)
    assert batch.site_url == grant.site_url
    fake_client = Mock(name="client")
    fake_client.name = "google_search_console"
    fake_client.inspect.return_value = Mock(
        status="INDEXED", http_status=200, verdict="PASS",
        coverage_state="Submitted and indexed", google_canonical="",
        last_crawl_time="",
    )
    execute_search_console_check(check_id=batch.checks.get().pk, client=fake_client)
    assert APIUsage.objects.get().project is None
    report = client.get(reverse("ranktracker:index_batch", args=[batch.pk]))
    assert b"Standalone URL checks" in report.content
    assert b"Indexed" in report.content
    client.force_login(outsider)
    assert client.get(reverse("ranktracker:index_batch", args=[batch.pk])).status_code == 404


@override_settings(GSC_SERVICE_ACCOUNT_FILE="/private/service-account.json")
def test_standalone_gsc_check_stops_after_grant_revocation(approved_project):
    grant = SearchConsoleGrant.objects.create(
        owner=approved_project.owner, site_url="sc-domain:example.com"
    )
    batch = queue_search_console_batch(
        actor=approved_project.owner, grant=grant, urls=["https://example.com/a"]
    )
    grant.is_active = False
    grant.save(update_fields=("is_active", "updated_at"))
    client = Mock(name="client")
    check = execute_search_console_check(check_id=batch.checks.get().pk, client=client)
    assert check.status == "CANCELLED"
    client.inspect.assert_not_called()
    assert APIUsage.objects.count() == 0


@override_settings(GSC_SERVICE_ACCOUNT_FILE="/private/service-account.json", GSC_DAILY_PROPERTY_LIMIT=1)
def test_gsc_queue_reserves_property_quota(approved_project):
    queue_search_console_batch(actor=approved_project.owner, project=approved_project, urls=["https://example.com/a"])
    with pytest.raises(ValidationError, match="limit"):
        queue_search_console_batch(actor=approved_project.owner, project=approved_project, urls=["https://example.com/b"])


@override_settings(GSC_SERVICE_ACCOUNT_FILE="/private/service-account.json")
def test_gsc_reservation_does_not_consume_serper_quota(approved_project):
    owner = approved_project.owner
    owner.monthly_request_quota = 1
    owner.save(update_fields=("monthly_request_quota",))
    country = Country.objects.create(name="India", iso_code="IN", google_country_code="in")
    location = Location.objects.create(owner=owner, country=country, city="Kolkata")
    approved_project.default_location = location
    approved_project.save(update_fields=("default_location", "updated_at"))
    queue_search_console_batch(actor=owner, project=approved_project, urls=["https://example.com/a"])
    assert queue_index_batch(actor=owner, project=approved_project, urls=["https://example.com/b"]).total == 1


@override_settings(GSC_SERVICE_ACCOUNT_FILE="/private/service-account.json")
def test_client_normalizes_google_inspection_without_network():
    credentials = Mock(token="private-token")
    response = Mock(status_code=200)
    response.json.return_value = {"inspectionResult": {"indexStatusResult": {
        "verdict": "PASS", "coverageState": "Submitted and indexed",
        "googleCanonical": "https://example.com/a", "lastCrawlTime": "2026-11-20T12:00:00Z",
    }}}
    with patch("apps.ranktracker.search_console._credentials_for_file", return_value=credentials), patch(
        "apps.ranktracker.search_console.requests.post", return_value=response
    ) as post:
        result = SearchConsoleClient().inspect(url="https://example.com/a", site_url="sc-domain:example.com")
    assert result.status == "INDEXED"
    assert post.call_args.kwargs["json"] == {
        "inspectionUrl": "https://example.com/a", "siteUrl": "sc-domain:example.com"
    }
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer private-token"


@override_settings(GSC_SERVICE_ACCOUNT_FILE="/private/service-account.json")
@pytest.mark.parametrize("verdict,expected", [("NEUTRAL", "NOT_INDEXED"), ("FAIL", "NOT_INDEXED"), ("VERDICT_UNSPECIFIED", "UNKNOWN")])
def test_client_verdicts_are_explicit(verdict, expected):
    response = Mock(status_code=200)
    response.json.return_value = {"inspectionResult": {"indexStatusResult": {"verdict": verdict}}}
    with patch("apps.ranktracker.search_console._credentials_for_file", return_value=Mock(token="token")), patch(
        "apps.ranktracker.search_console.requests.post", return_value=response
    ):
        assert SearchConsoleClient().inspect(url="https://example.com/a", site_url="sc-domain:example.com").status == expected


@override_settings(GSC_SERVICE_ACCOUNT_FILE="/private/service-account.json")
@pytest.mark.parametrize("http_status,expected", [(403, "ACCESS_ERROR"), (429, "RATE_LIMITED")])
def test_client_access_and_quota_errors_are_inconclusive(http_status, expected):
    with patch("apps.ranktracker.search_console._credentials_for_file", return_value=Mock(token="token")), patch(
        "apps.ranktracker.search_console.requests.post", return_value=Mock(status_code=http_status)
    ):
        result = SearchConsoleClient().inspect(url="https://example.com/a", site_url="sc-domain:example.com")
    assert result.status == expected
    assert result.http_status == http_status


@override_settings(GSC_SERVICE_ACCOUNT_FILE="/private/service-account.json")
def test_inspection_history_and_usage_are_scoped(approved_project):
    batch = queue_search_console_batch(actor=approved_project.owner, project=approved_project, urls=["https://example.com/a"])
    client = Mock(name="client")
    client.name = "google_search_console"
    client.inspect.return_value = Mock(
        status="NOT_INDEXED", http_status=200, verdict="NEUTRAL",
        coverage_state="Discovered - currently not indexed", google_canonical="",
        last_crawl_time="",
    )
    check = execute_search_console_check(check_id=batch.checks.get().pk, client=client)
    assert check.status == "NOT_INDEXED"
    assert check.coverage_state == "Discovered - currently not indexed"
    assert batch.checks.count() == 1
    assert APIUsage.objects.filter(user=approved_project.owner, provider="google_search_console").count() == 1
    batch.refresh_from_db()
    assert (batch.status, batch.completed) == ("COMPLETED", 1)
