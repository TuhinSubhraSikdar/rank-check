from unittest.mock import Mock
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.locations.models import Country, Location
from apps.projects.models import Project
from apps.ranktracker.indexing import IndexBatchForm, execute_index_check, queue_index_batch
from apps.ranktracker.models import IndexCheck
from apps.serp_providers.base import OrganicResult, SearchResult, SearchStatus
from apps.usage.models import APIUsage

pytestmark = pytest.mark.django_db


@pytest.fixture
def project():
    owner = User.objects.create_user("alice", "alice@example.com", "password-long-enough")
    country = Country.objects.create(name="United States", iso_code="US", google_country_code="us")
    location = Location.objects.create(owner=owner, country=country, city="New York")
    return Project.objects.create(owner=owner, name="Example", website_url="https://example.com", default_location=location)


def result(*, organic=(), status=SearchStatus.SUCCESS):
    return SearchResult(keyword="site:https://example.com/a", location="New York", country="US", language="en", organic_results=organic, status=status, actual_checked_depth=10, request_metadata={"request_id": str(uuid4()), "http_status": 200, "requested_results": 10})


def test_form_sorts_cleans_deduplicates_and_restricts_domain(project):
    form = IndexBatchForm(data={"project": project.pk, "urls": "https://example.com/z#fragment\nhttps://example.com/a\nhttps://example.com/z"}, actor=project.owner)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["cleaned_urls"] == ["https://example.com/a", "https://example.com/z"]
    form = IndexBatchForm(data={"project": project.pk, "urls": "https://example.com.evil.test/a"}, actor=project.owner)
    assert not form.is_valid()
    assert "outside" in str(form.errors)


def test_batch_quota_and_tenant_isolation(project, client):
    other = User.objects.create_user("bob", "bob@example.com", "password-long-enough")
    assert not IndexBatchForm(data={"project": project.pk, "urls": "https://example.com/a"}, actor=other).is_valid()
    with pytest.raises(PermissionDenied):
        queue_index_batch(actor=other, project=project, urls=["https://example.com/a"])
    client.force_login(other)
    assert client.get(reverse("ranktracker:index_batch", args=[999])).status_code == 404
    project.owner.monthly_request_quota = 1
    project.owner.save(update_fields=("monthly_request_quota",))
    batch = queue_index_batch(actor=project.owner, project=project, urls=["https://example.com/a"])
    assert client.get(reverse("ranktracker:index_batch", args=[batch.pk])).status_code == 404
    with pytest.raises(ValidationError, match="quota"):
        queue_index_batch(actor=project.owner, project=project, urls=["https://example.com/b"])


def test_exact_match_and_absence_are_reported_honestly(project):
    batch = queue_index_batch(actor=project.owner, project=project, urls=["https://example.com/a", "https://example.com/b"])
    checks = list(batch.checks.order_by("url"))
    provider = Mock(name="provider")
    provider.name = "serper"
    provider.search.side_effect = [
        result(organic=(OrganicResult(position=1, title="A", link="https://example.com/a/"),)),
        result(organic=(OrganicResult(position=1, title="Other", link="https://example.com/b-child"),), status=SearchStatus.INCOMPLETE),
    ]
    execute_index_check(check_id=checks[0].pk, provider=provider)
    execute_index_check(check_id=checks[1].pk, provider=provider)
    assert [IndexCheck.objects.get(pk=item.pk).status for item in checks] == ["FOUND", "NOT_CONFIRMED"]
    assert APIUsage.objects.filter(user=project.owner, project=project).count() == 2
    batch.refresh_from_db()
    assert (batch.status, batch.completed) == ("COMPLETED", 2)
    assert provider.search.call_args_list[0].kwargs["keyword"] == "site:https://example.com/a"


def test_provider_error_is_inconclusive_and_does_not_fetch_url(project):
    batch = queue_index_batch(actor=project.owner, project=project, urls=["https://example.com/a"])
    provider = Mock(name="provider")
    provider.name = "serper"
    provider.search.return_value = result(status=SearchStatus.TIMEOUT)
    execute_index_check(check_id=batch.checks.get().pk, provider=provider)
    assert batch.checks.get().status == "TIMEOUT"
    assert APIUsage.objects.count() == 1


def test_paste_flow_creates_private_report_without_provider_request(project, client):
    client.force_login(project.owner)
    response = client.post(reverse("ranktracker:index_new"), {
        "project": project.pk,
        "urls": "https://example.com/z\nhttps://example.com/a\nhttps://example.com/z#section",
    })
    assert response.status_code == 302
    batch = project.index_batches.get()
    assert batch.total == 2
    assert list(batch.checks.values_list("url", flat=True)) == ["https://example.com/a", "https://example.com/z"]
    report = client.get(reverse("ranktracker:index_batch", args=[batch.pk]))
    assert report.status_code == 200
    assert b"Not found in search" in report.content
    assert APIUsage.objects.count() == 0


def test_standalone_serper_check_uses_owned_location_and_has_private_report(project, client):
    owner = project.owner
    location = project.default_location
    other = User.objects.create_user("other", "other@example.com", "password-long-enough")
    form = IndexBatchForm(data={
        "method": "SERPER", "location": location.pk,
        "urls": "https://outside.test/page\nhttps://outside.test/page#section",
    }, actor=owner)
    assert form.is_valid(), form.errors
    assert form.cleaned_data["cleaned_urls"] == ["https://outside.test/page"]
    assert not IndexBatchForm(data={
        "method": "SERPER", "location": location.pk,
        "urls": "https://outside.test/page",
    }, actor=other).is_valid()
    with pytest.raises(ValidationError):
        queue_index_batch(actor=other, location=location, urls=["https://outside.test/page"])
    client.force_login(owner)
    response = client.post(reverse("ranktracker:index_new"), {
        "method": "SERPER", "location": location.pk,
        "urls": "https://outside.test/page",
    })
    assert response.status_code == 302
    batch = owner.index_batches.get()
    assert batch.project is None
    assert batch.location == location
    provider = Mock(name="provider")
    provider.name = "serper"
    provider.search.return_value = result(organic=(OrganicResult(
        position=1, title="Page", link="https://outside.test/page"
    ),))
    execute_index_check(check_id=batch.checks.get().pk, provider=provider)
    assert batch.checks.get().status == "FOUND"
    assert provider.search.call_args.kwargs["language"] == location.language_code
    assert APIUsage.objects.get().project is None
    assert b"Standalone URL checks" in client.get(reverse("ranktracker:index_batch", args=[batch.pk])).content
    client.force_login(other)
    assert client.get(reverse("ranktracker:index_batch", args=[batch.pk])).status_code == 404


def test_standalone_serper_check_does_not_run_after_location_archived(project):
    location = project.default_location
    batch = queue_index_batch(actor=project.owner, location=location, urls=["https://outside.test/page"])
    location.is_active = False
    location.save(update_fields=("is_active", "updated_at"))
    provider = Mock(name="provider")
    check = execute_index_check(check_id=batch.checks.get().pk, provider=provider)
    assert check.status == "CANCELLED"
    provider.search.assert_not_called()
    assert APIUsage.objects.count() == 0


def test_quick_index_check_needs_only_urls_and_keeps_report_private(project, client):
    owner = project.owner
    client.force_login(owner)
    form_page = client.get(reverse("ranktracker:index_quick"))
    assert form_page.status_code == 200
    assert b"name=\"urls\"" in form_page.content
    assert b"name=\"project\"" not in form_page.content
    assert b"name=\"location\"" not in form_page.content
    response = client.post(reverse("ranktracker:index_quick"), {
        "urls": "https://example.com/a#fragment\nhttps://example.com/a",
    })
    assert response.status_code == 302
    batch = owner.index_batches.get(project__isnull=True)
    assert batch.location is None
    assert batch.total == 1
    provider = Mock(name="provider")
    provider.name = "serper"
    provider.search.return_value = result(organic=())
    execute_index_check(check_id=batch.checks.get().pk, provider=provider)
    assert provider.search.call_args.kwargs["keyword"] == "site:https://example.com/a"
    assert provider.search.call_args.kwargs["location"] is None
    assert provider.search.call_args.kwargs["language"] == "en"
    report = client.get(reverse("ranktracker:index_batch", args=[batch.pk]))
    assert b"Not found in search" in report.content
    outsider = User.objects.create_user("outsider", "outsider@example.com", "password-long-enough")
    client.force_login(outsider)
    assert client.get(reverse("ranktracker:index_batch", args=[batch.pk])).status_code == 404


@override_settings(SERPER_API_KEY="")
def test_quick_index_check_refuses_unconfigured_api_key(project, client):
    client.force_login(project.owner)
    response = client.post(reverse("ranktracker:index_quick"), {
        "urls": "https://example.com/a",
    })
    assert response.status_code == 200
    assert b"Serper API key is not configured" in response.content
    assert not project.owner.index_batches.exists()
