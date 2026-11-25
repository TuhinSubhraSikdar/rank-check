from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.keywords.services import owned_keywords

from .models import KeywordLocation


def ensure_project_default_configurations(*, project, keywords=None):
    if not project.default_location_id:
        return 0
    if project.default_location.owner_id != project.owner_id or not project.default_location.is_active:
        raise PermissionDenied
    if keywords is None:
        keywords = project.keywords.filter(is_active=True)
    configurations = [KeywordLocation(keyword=keyword, location_id=project.default_location_id, device="DEFAULT", requested_depth=10, source=KeywordLocation.Source.PROJECT) for keyword in keywords]
    KeywordLocation.objects.bulk_create(configurations, ignore_conflicts=True, batch_size=500)
    keyword_ids = [item.keyword_id for item in configurations]
    if keyword_ids:
        KeywordLocation.objects.filter(keyword_id__in=keyword_ids, location_id=project.default_location_id, device="DEFAULT", is_active=False).update(is_active=True, source=KeywordLocation.Source.PROJECT)
    return len(configurations)


def sync_project_default_location(*, project, previous_location_id):
    if previous_location_id != project.default_location_id and previous_location_id:
        KeywordLocation.objects.filter(
            keyword__project=project,
            location_id=previous_location_id,
            source=KeywordLocation.Source.PROJECT,
            is_active=True,
        ).update(is_active=False)
    if project.default_location_id:
        ensure_project_default_configurations(project=project)


def owned_configurations(actor):
    return KeywordLocation.objects.filter(keyword__project__owner=actor, is_active=True).select_related("keyword", "keyword__project", "location", "location__country")


@transaction.atomic
def save_configuration(*, actor, keyword_id, form):
    keyword = owned_keywords(actor).get(pk=keyword_id)
    configuration = form.save(commit=False)
    if configuration.location.owner_id != actor.id:
        raise PermissionDenied
    configuration.keyword = keyword
    configuration.save()
    return configuration
