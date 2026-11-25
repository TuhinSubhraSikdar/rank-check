from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SearchStatus(str, Enum):
    SUCCESS = "SUCCESS"
    NOT_FOUND = "NOT_FOUND"
    API_ERROR = "API_ERROR"
    TIMEOUT = "TIMEOUT"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True)
class ProviderCapabilities:
    max_verified_depth: int
    supports_location: bool
    supports_country: bool
    supports_language: bool
    supports_device: bool
    supports_pagination: bool


@dataclass(frozen=True)
class OrganicResult:
    position: int
    title: str
    link: str
    snippet: str = ""


@dataclass(frozen=True)
class SearchResult:
    keyword: str
    location: str
    country: str
    language: str
    organic_results: tuple[OrganicResult, ...] = ()
    status: SearchStatus = SearchStatus.SUCCESS
    actual_checked_depth: int = 0
    request_metadata: dict[str, Any] = field(default_factory=dict)
    error_message: str = ""


class BaseSERPProvider(ABC):
    name: str
    capabilities: ProviderCapabilities

    @abstractmethod
    def search(self, *, keyword, location, language, device, depth) -> SearchResult:
        raise NotImplementedError
