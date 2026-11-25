from unittest.mock import Mock
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.keywords.models import Keyword
from apps.locations.models import Country, Location
from apps.projects.models import Project
from apps.ranktracker.engine import create_check, domain_matches, execute_check
from apps.ranktracker.models import KeywordLocation
from apps.serp_providers.base import OrganicResult, SearchResult, SearchStatus
from apps.usage.models import APIUsage

pytestmark = pytest.mark.django_db


def setup_configuration():
    user = User.objects.create_user("owner", "owner@example.com", "strong-password-534")
    project = Project.objects.create(owner=user, name="Site", website_url="https://example.com", root_domain="example.com")
    keyword = Keyword.objects.create(project=project, text="seo")
    country = Country.objects.create(name="India", iso_code="IN", google_country_code="in")
    location = Location.objects.create(owner=user, country=country, city="Kolkata")
    return user, KeywordLocation.objects.create(keyword=keyword, location=location)


def provider_result(position=None, status=SearchStatus.SUCCESS):
    organic = tuple(OrganicResult(i, f"R{i}", "https://example.com/page" if i == position else f"https://site{i}.test") for i in range(1, 11))
    return SearchResult("seo", "Kolkata", "IN", "en", organic, status, 10, {"request_id": str(uuid4()), "http_status": 200, "requested_results": 10, "duration_ms": 15})


def test_domain_boundary_matching():
    assert domain_matches("https://shop.example.com/x", "example.com")
    assert not domain_matches("https://example.com.fake.test", "example.com")
    assert not domain_matches("https://shop.example.com", "example.com", False)


def test_rank_movement_and_usage():
    user, config = setup_configuration()
    provider = Mock()
    provider.name = "serper"
    provider.search.side_effect = [provider_result(8), provider_result(2)]
    first = execute_check(check_id=create_check(actor=user, configuration=config).id, provider=provider)
    second = execute_check(check_id=create_check(actor=user, configuration=config).id, provider=provider)
    assert first.result.position == 8
    assert (second.result.position, second.result.previous_position, second.result.movement) == (2, 8, 6)
    assert APIUsage.objects.count() == 2


def test_not_found_then_newly_ranked_and_immutability():
    user, config = setup_configuration()
    provider = Mock()
    provider.name = "serper"
    provider.search.side_effect = [provider_result(None), provider_result(4)]
    missing = execute_check(check_id=create_check(actor=user, configuration=config).id, provider=provider)
    ranked = execute_check(check_id=create_check(actor=user, configuration=config).id, provider=provider)
    assert missing.result.status == "NOT_FOUND"
    assert ranked.result.is_newly_ranked
    ranked.result.position = 3
    with pytest.raises(ValidationError):
        ranked.result.save()
