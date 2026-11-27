"""Read-only Google Search Console URL Inspection adapter.

Credentials come only from a deployment-owned service account file. Tenant
access is granted separately by a superuser through SearchConsoleGrant.
"""

from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlsplit

import requests
from django.conf import settings
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from apps.ranktracker.engine import domain_matches

INSPECTION_ENDPOINT = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
READONLY_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"


@lru_cache(maxsize=2)
def _credentials_for_file(path):
    return service_account.Credentials.from_service_account_file(path, scopes=[READONLY_SCOPE])


def property_covers_url(site_url: str, url: str) -> bool:
    if site_url.startswith("sc-domain:"):
        domain = site_url.removeprefix("sc-domain:").strip().lower()
        return bool(domain and "." in domain and domain_matches(url, domain, True))
    property_parts = urlsplit(site_url)
    url_parts = urlsplit(url)
    return bool(
        property_parts.scheme in {"http", "https"}
        and property_parts.hostname
        and not property_parts.username
        and not property_parts.password
        and not property_parts.query
        and not property_parts.fragment
        and site_url.endswith("/")
        and url_parts.scheme == property_parts.scheme
        and url_parts.netloc.lower() == property_parts.netloc.lower()
        and (url_parts.path or "/").startswith(property_parts.path)
    )


@dataclass(frozen=True)
class Inspection:
    status: str
    http_status: int | None = None
    verdict: str = ""
    coverage_state: str = ""
    google_canonical: str = ""
    last_crawl_time: str = ""


class SearchConsoleClient:
    name = "google_search_console"

    def inspect(self, *, url: str, site_url: str) -> Inspection:
        if not property_covers_url(site_url, url):
            return Inspection(status="INVALID_RESPONSE")
        credential_file = settings.GSC_SERVICE_ACCOUNT_FILE
        if not credential_file:
            return Inspection(status="API_ERROR")
        try:
            credentials = _credentials_for_file(credential_file)
            if not credentials.valid:
                credentials.refresh(Request())
            response = requests.post(
                INSPECTION_ENDPOINT,
                headers={"Authorization": f"Bearer {credentials.token}", "Accept": "application/json"},
                json={"inspectionUrl": url, "siteUrl": site_url},
                timeout=settings.GSC_TIMEOUT,
            )
        except requests.Timeout:
            return Inspection(status="TIMEOUT")
        except (OSError, ValueError, GoogleAuthError, requests.RequestException):
            return Inspection(status="API_ERROR")
        if response.status_code == 429:
            return Inspection(status="RATE_LIMITED", http_status=429)
        if response.status_code in {401, 403}:
            return Inspection(status="ACCESS_ERROR", http_status=response.status_code)
        if response.status_code != 200:
            return Inspection(status="API_ERROR", http_status=response.status_code)
        try:
            data = response.json()
            result = data["inspectionResult"]["indexStatusResult"]
            if not isinstance(result, dict):
                raise ValueError
            verdict = result["verdict"]
            if verdict not in {"PASS", "NEUTRAL", "FAIL", "VERDICT_UNSPECIFIED"}:
                raise ValueError
            status = {"PASS": "INDEXED", "NEUTRAL": "NOT_INDEXED", "FAIL": "NOT_INDEXED"}.get(verdict, "UNKNOWN")
            return Inspection(
                status=status,
                http_status=200,
                verdict=verdict,
                coverage_state=str(result.get("coverageState", ""))[:500],
                google_canonical=str(result.get("googleCanonical", ""))[:1000],
                last_crawl_time=str(result.get("lastCrawlTime", "")),
            )
        except (KeyError, TypeError, ValueError):
            return Inspection(status="INVALID_RESPONSE", http_status=200)
