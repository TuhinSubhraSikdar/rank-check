from urllib.parse import urlsplit
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.competitors.models import CompetitorResult
from apps.serp_providers.base import SearchStatus
from apps.usage.models import APIUsage

from .models import RankCheck, RankingResult


def domain_matches(url, domain, include_subdomains=True):
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    domain = domain.lower().rstrip(".")
    if not host or not domain:
        return False
    return host == domain or (include_subdomains and host.endswith("." + domain))


@transaction.atomic
def create_check(*, actor, configuration):
    if configuration.keyword.project.owner_id != actor.id:
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied
    return RankCheck.objects.create(configuration=configuration, requested_depth=configuration.requested_depth)


def execute_check(*, check_id, provider):
    with transaction.atomic():
        check = RankCheck.objects.select_for_update().select_related("configuration__keyword__project", "configuration__location__country").get(pk=check_id)
        if check.status not in {"PENDING", "QUEUED"} or (check.job_id and check.job.cancelled):
            return check
        config = check.configuration
        if not all((config.is_active, config.keyword.is_active, config.keyword.project.is_active, config.location.is_active)):
            check.status = "CANCELLED"
            check.completed_at = timezone.now()
            check.save(update_fields=("status", "completed_at", "updated_at"))
            return check
        check.status = "RUNNING"
        check.started_at = timezone.now()
        check.save(update_fields=("status", "started_at", "updated_at"))
    config = check.configuration
    result = provider.search(keyword=config.keyword.text, location=config.location, language=config.location.language_code, device=config.device, depth=check.requested_depth)
    with transaction.atomic():
        check = RankCheck.objects.select_for_update().get(pk=check_id)
        metadata = result.request_metadata
        request_id = UUID(metadata["request_id"])
        APIUsage.objects.create(user=config.keyword.project.owner, project=config.keyword.project, provider=provider.name, request_identifier=request_id, status=result.status.value, http_status=metadata.get("http_status"), requested_results=metadata.get("requested_results", 10), actual_checked_depth=result.actual_checked_depth, duration_ms=metadata.get("duration_ms"))
        check.request_identifier = request_id
        check.actual_checked_depth = result.actual_checked_depth
        check.status = result.status.value
        check.error_message = result.error_message[:500]
        check.completed_at = timezone.now()
        project = config.keyword.project
        matches = [item for item in result.organic_results if domain_matches(item.link, project.root_domain, project.match_subdomains)]
        selected = min(matches, key=lambda item: item.position) if matches else None
        if selected or result.status in {SearchStatus.SUCCESS, SearchStatus.INCOMPLETE}:
            previous = RankingResult.objects.filter(rank_check__configuration=config).order_by("-checked_at").first()
            position = selected.position if selected else None
            status = SearchStatus.SUCCESS.value if selected else result.status.value
            if not selected and result.status == SearchStatus.SUCCESS:
                status = SearchStatus.NOT_FOUND.value
            previous_ranked = RankingResult.objects.filter(rank_check__configuration=config, position__isnull=False).order_by("-checked_at").first()
            RankingResult.objects.create(rank_check=check, status=status, position=position, ranking_url=selected.link if selected else "", serp_title=selected.title if selected else "", previous_position=previous_ranked.position if previous_ranked else None, movement=(previous_ranked.position - position) if previous_ranked and position else None, is_newly_ranked=bool(position and previous and previous.position is None))
            for competitor in project.competitors.filter(is_active=True):
                candidate = min((item for item in result.organic_results if domain_matches(item.link, competitor.domain)), key=lambda item: item.position, default=None)
                if candidate:
                    CompetitorResult.objects.create(rank_check=check, competitor=competitor, position=candidate.position, ranking_url=candidate.link, checked_at=check.completed_at)
        check.save(update_fields=("request_identifier", "actual_checked_depth", "status", "error_message", "completed_at", "updated_at"))
        return check
