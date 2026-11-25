from django.core.exceptions import PermissionDenied
from django.db import transaction

from .models import Location


def owned_locations(actor, *, include_archived=False):
    queryset = Location.objects.filter(owner=actor).select_related("country")
    return queryset if include_archived else queryset.filter(is_active=True, country__is_active=True)


@transaction.atomic
def save_location(*, actor, form):
    location = form.save(commit=False)
    if location.pk and location.owner_id != actor.id:
        raise PermissionDenied
    location.owner = actor
    location.save()
    project = form.cleaned_data.get("project")
    if project:
        if project.owner_id != actor.id:
            raise PermissionDenied
        previous_location_id = project.default_location_id
        project.default_location = location
        project.save(update_fields=("default_location", "updated_at"))
        from apps.ranktracker.services import sync_project_default_location

        sync_project_default_location(project=project, previous_location_id=previous_location_id)
    return location


@transaction.atomic
def archive_location(*, actor, location_id):
    location = owned_locations(actor).select_for_update().get(pk=location_id)
    location.is_active = False
    location.save(update_fields=("is_active", "updated_at"))
    from apps.projects.models import Project
    from apps.ranktracker.models import KeywordLocation

    Project.objects.filter(owner=actor, default_location=location).update(default_location=None)
    KeywordLocation.objects.filter(location=location, source=KeywordLocation.Source.PROJECT).update(is_active=False)
    return location
