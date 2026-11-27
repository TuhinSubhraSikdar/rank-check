from unittest.mock import Mock

import pytest
import requests

from apps.accounts.models import User
from apps.locations.models import Country, Location
from apps.projects.models import Project
from apps.serp_providers.base import SearchStatus
from apps.serp_providers.serper import SerperProvider

pytestmark = pytest.mark.django_db


@pytest.fixture
def location():
    user = User.objects.create_user("alice", "a@example.com", "strong-password-534")
    country = Country.objects.create(name="United States", iso_code="US", google_country_code="us")
    return Location.objects.create(owner=user, country=country, city="New York", provider_location_name="New York, New York, United States")


def response(status=200, payload=None):
    value = Mock(status_code=status)
    value.json.return_value = payload
    return value


def test_serper_request_and_normalization(location):
    session = Mock()
    session.post.return_value = response(payload={"organic": [{"position": number, "title": f"Result {number}", "link": f"https://example{number}.com", "snippet": "Text"} for number in range(1, 11)]})
    provider = SerperProvider(api_key="secret", session=session, base_url="https://google.serper.dev/search", timeout=7)
    result = provider.search(keyword="seo agency", location=location, language="en", device=Project.Device.PROVIDER_DEFAULT, depth=10)
    assert result.status == SearchStatus.SUCCESS
    assert result.actual_checked_depth == 10
    call = session.post.call_args
    assert call.kwargs["json"] == {"q": "seo agency", "location": "New York, New York, United States", "gl": "us", "hl": "en", "num": 10}
    assert call.kwargs["headers"]["X-API-KEY"] == "secret"
    assert "secret" not in str(result.request_metadata)


def test_serper_site_search_without_location_uses_us_english_defaults():
    session = Mock()
    session.post.return_value = response(payload={"organic": []})
    provider = SerperProvider(api_key="secret", session=session)
    result = provider.search(
        keyword="site:https://example.com/page", location=None,
        language="en", device="DEFAULT", depth=10,
    )
    assert session.post.call_args.kwargs["json"] == {
        "q": "site:https://example.com/page", "gl": "us", "hl": "en", "num": 10,
    }
    assert result.status == SearchStatus.INCOMPLETE
    assert result.country == "US"
    assert result.location == "United States (no city)"
    session.post.side_effect = requests.Timeout()
    assert provider.search(
        keyword="site:https://example.com/page", location=None,
        language="en", device="DEFAULT", depth=10,
    ).status == SearchStatus.TIMEOUT


def test_serper_incomplete_and_invalid_response(location):
    session = Mock()
    session.post.return_value = response(payload={"organic": [{"position": 1, "link": "https://a.example"}, {"position": 3, "link": "https://c.example"}]})
    provider = SerperProvider(api_key="secret", session=session)
    result = provider.search(keyword="term", location=location, language="en", device="DEFAULT", depth=10)
    assert (result.status, result.actual_checked_depth) == (SearchStatus.INCOMPLETE, 1)
    session.post.return_value = response(payload={"organic": [{"position": "1", "link": "https://a.example"}]})
    assert provider.search(keyword="term", location=location, language="en", device="DEFAULT", depth=10).status == SearchStatus.INVALID_RESPONSE


def test_serper_errors_and_capability_guards(location):
    session = Mock()
    session.post.side_effect = requests.Timeout()
    provider = SerperProvider(api_key="secret", session=session)
    assert provider.search(keyword="term", location=location, language="en", device="DEFAULT", depth=10).status == SearchStatus.TIMEOUT
    with pytest.raises(ValueError, match="Top 10"):
        provider.search(keyword="term", location=location, language="en", device="DEFAULT", depth=50)
    with pytest.raises(ValueError, match="device-specific"):
        provider.search(keyword="term", location=location, language="en", device="MOBILE", depth=10)


def test_serper_http_error_hides_provider_body(location):
    session = Mock()
    session.post.return_value = response(status=429, payload={"message": "secret diagnostics"})
    result = SerperProvider(api_key="secret", session=session).search(keyword="term", location=location, language="en", device="DEFAULT", depth=10)
    assert result.status == SearchStatus.API_ERROR
    assert "secret diagnostics" not in result.error_message
