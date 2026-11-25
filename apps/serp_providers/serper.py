import time
import uuid

import requests
from django.conf import settings

from apps.projects.models import Project

from .base import BaseSERPProvider, OrganicResult, ProviderCapabilities, SearchResult, SearchStatus


class SerperProvider(BaseSERPProvider):
    name = "serper"
    capabilities = ProviderCapabilities(
        max_verified_depth=10,
        supports_location=True,
        supports_country=True,
        supports_language=True,
        supports_device=False,
        supports_pagination=True,
    )

    def __init__(self, *, api_key=None, base_url=None, timeout=None, session=None):
        self.api_key = settings.SERPER_API_KEY if api_key is None else api_key
        self.base_url = settings.SERPER_BASE_URL if base_url is None else base_url
        self.timeout = settings.SERPER_TIMEOUT if timeout is None else timeout
        self.session = session or requests.Session()

    def _validate(self, *, device, depth):
        if not self.api_key:
            raise ValueError("SERPER_API_KEY is not configured.")
        if device != Project.Device.PROVIDER_DEFAULT:
            raise ValueError("Serper device-specific search is not verified; use provider default.")
        if depth != 10:
            raise ValueError("Only Top 10 has verified absolute position semantics for Serper.")

    def search(self, *, keyword, location, language, device, depth):
        self._validate(device=device, depth=depth)
        request_id = str(uuid.uuid4())
        payload = {
            "q": keyword,
            "location": location.provider_location_name or location.display_name,
            "gl": location.country.google_country_code,
            "hl": language,
            "num": 10,
        }
        started = time.monotonic()
        metadata = {"request_id": request_id, "endpoint": self.base_url, "page": 1, "requested_results": 10}
        try:
            response = self.session.post(
                self.base_url,
                json=payload,
                headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                timeout=self.timeout,
            )
        except requests.Timeout:
            return self._error(SearchStatus.TIMEOUT, keyword, location, language, metadata, started, "Provider request timed out.")
        except requests.RequestException as exc:
            return self._error(SearchStatus.API_ERROR, keyword, location, language, metadata, started, f"Provider transport error: {exc.__class__.__name__}.")
        metadata = {**metadata, "http_status": response.status_code, "duration_ms": round((time.monotonic() - started) * 1000)}
        if response.status_code >= 400:
            return SearchResult(keyword=keyword, location=location.display_name, country=location.country.iso_code, language=language, status=SearchStatus.API_ERROR, request_metadata=metadata, error_message="Provider rejected the request.")
        try:
            data = response.json()
        except ValueError:
            return SearchResult(keyword=keyword, location=location.display_name, country=location.country.iso_code, language=language, status=SearchStatus.INVALID_RESPONSE, request_metadata=metadata, error_message="Provider returned non-JSON content.")
        organic = data.get("organic") if isinstance(data, dict) else None
        if not isinstance(organic, list):
            return SearchResult(keyword=keyword, location=location.display_name, country=location.country.iso_code, language=language, status=SearchStatus.INVALID_RESPONSE, request_metadata=metadata, error_message="Provider response has no organic result list.")
        normalized = []
        for item in organic:
            if not isinstance(item, dict) or not isinstance(item.get("position"), int) or not isinstance(item.get("link"), str):
                return SearchResult(keyword=keyword, location=location.display_name, country=location.country.iso_code, language=language, status=SearchStatus.INVALID_RESPONSE, request_metadata=metadata, error_message="Organic result fields are invalid.")
            position = item["position"]
            if position < 1:
                return SearchResult(keyword=keyword, location=location.display_name, country=location.country.iso_code, language=language, status=SearchStatus.INVALID_RESPONSE, request_metadata=metadata, error_message="Organic position must be positive.")
            normalized.append(OrganicResult(position=position, title=str(item.get("title", "")), link=item["link"], snippet=str(item.get("snippet", ""))))
        normalized.sort(key=lambda result: result.position)
        contiguous_depth = 0
        for result in normalized:
            if result.position == contiguous_depth + 1:
                contiguous_depth = result.position
            elif result.position > contiguous_depth + 1:
                break
        status = SearchStatus.SUCCESS if contiguous_depth >= depth else SearchStatus.INCOMPLETE
        return SearchResult(keyword=keyword, location=location.display_name, country=location.country.iso_code, language=language, organic_results=tuple(normalized), status=status, actual_checked_depth=contiguous_depth, request_metadata=metadata)

    @staticmethod
    def _error(status, keyword, location, language, metadata, started, message):
        return SearchResult(keyword=keyword, location=location.display_name, country=location.country.iso_code, language=language, status=status, request_metadata={**metadata, "duration_ms": round((time.monotonic() - started) * 1000)}, error_message=message)
