from apps.keywords.models import Keyword
from apps.projects.models import Project
from apps.ranktracker.models import KeywordLocation, RankingResult


def latest_results(actor):
    queryset = RankingResult.objects.filter(rank_check__configuration__keyword__project__owner=actor).select_related("rank_check__configuration__keyword__project", "rank_check__configuration__location__country")
    seen = set()
    for result in queryset.order_by("-checked_at", "-id").iterator(chunk_size=500):
        config_id = result.rank_check.configuration_id
        if config_id not in seen:
            seen.add(config_id)
            yield result


def dashboard_metrics(actor):
    results = list(latest_results(actor))
    ranked = [item for item in results if item.position is not None]
    return {
        "projects": Project.objects.filter(owner=actor, is_active=True).count(),
        "keywords": Keyword.objects.filter(project__owner=actor, is_active=True, project__is_active=True).count(),
        "configurations": KeywordLocation.objects.filter(keyword__project__owner=actor, is_active=True).count(),
        "top3": sum(item.position <= 3 for item in ranked),
        "top10": sum(item.position <= 10 for item in ranked),
        "top20": sum(item.position <= 20 for item in ranked),
        "improved": sum(item.movement is not None and item.movement > 0 for item in ranked),
        "declined": sum(item.movement is not None and item.movement < 0 for item in ranked),
        "unchanged": sum(item.movement == 0 for item in ranked),
        "not_found": sum(item.status == "NOT_FOUND" for item in results),
        "average_position": round(sum(item.position for item in ranked) / len(ranked), 1) if ranked else None,
        "last_update": max((item.checked_at for item in results), default=None),
        "results": results[:20],
    }
