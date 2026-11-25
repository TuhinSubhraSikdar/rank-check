from unittest.mock import Mock
from uuid import uuid4

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.competitors.models import Competitor, CompetitorResult
from apps.keywords.models import Keyword
from apps.locations.models import Country, Location
from apps.projects.models import Project
from apps.ranktracker.engine import create_check, execute_check
from apps.ranktracker.models import KeywordLocation
from apps.serp_providers.base import OrganicResult, SearchResult, SearchStatus

pytestmark = pytest.mark.django_db


def test_competitor_uses_same_serp_and_owner_scoping(client):
    owner = User.objects.create_user("owner", "owner@example.com", "strong-password-534")
    other = User.objects.create_user("other", "other@example.com", "strong-password-534")
    project = Project.objects.create(owner=owner, name="Site", website_url="https://example.com", root_domain="example.com")
    competitor = Competitor.objects.create(project=project, name="Rival", domain="rival.test")
    country = Country.objects.create(name="India", iso_code="IN", google_country_code="in")
    location = Location.objects.create(owner=owner, country=country, city="Kolkata")
    config = KeywordLocation.objects.create(keyword=Keyword.objects.create(project=project, text="seo"), location=location)
    provider = Mock()
    provider.name = "serper"
    organic = tuple(OrganicResult(i, f"Result {i}", "https://rival.test/page" if i == 3 else f"https://site{i}.test") for i in range(1, 11))
    provider.search.return_value = SearchResult("seo", "Kolkata", "IN", "en", organic, SearchStatus.SUCCESS, 10, {"request_id": str(uuid4())})
    execute_check(check_id=create_check(actor=owner, configuration=config).id, provider=provider)
    assert CompetitorResult.objects.get(competitor=competitor).position == 3
    assert provider.search.call_count == 1
    client.force_login(other)
    assert client.get(reverse("competitors:list", args=[project.id])).status_code == 404
