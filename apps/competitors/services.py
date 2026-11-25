from django.core.exceptions import PermissionDenied
from django.db import transaction

from .models import Competitor


def owned_competitors(actor, project=None):
    queryset = Competitor.objects.filter(project__owner=actor, is_active=True).select_related("project")
    if project is not None:
        if project.owner_id != actor.id:
            raise PermissionDenied
        queryset = queryset.filter(project=project)
    return queryset


@transaction.atomic
def save_competitor(*, actor, project, form):
    if project.owner_id != actor.id:
        raise PermissionDenied
    competitor = form.save(commit=False)
    if competitor.pk and competitor.project_id != project.id:
        raise PermissionDenied
    competitor.project = project
    competitor.save()
    return competitor
