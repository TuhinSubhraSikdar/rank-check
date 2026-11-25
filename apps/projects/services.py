from django.core.exceptions import PermissionDenied
from django.db import transaction

from .forms import ProjectForm
from .models import Project


def owned_projects(actor, *, include_archived=False):
    queryset = Project.objects.filter(owner=actor)
    return queryset if include_archived else queryset.filter(is_active=True)


@transaction.atomic
def save_project(*, actor, data, instance=None):
    if instance is not None and instance.owner_id != actor.id:
        raise PermissionDenied
    previous_location_id = None
    if instance is not None:
        previous_location_id = Project.objects.filter(pk=instance.pk).values_list("default_location_id", flat=True).first()
    form = ProjectForm(data=data, instance=instance, actor=actor)
    if not form.is_valid():
        return None, form
    project = form.save(commit=False)
    project.owner = actor
    project.save()
    from apps.ranktracker.services import sync_project_default_location

    sync_project_default_location(project=project, previous_location_id=previous_location_id)
    return project, form


@transaction.atomic
def archive_project(*, actor, project_id):
    project = owned_projects(actor).select_for_update().get(pk=project_id)
    project.is_active = False
    project.save(update_fields=("is_active", "updated_at"))
    return project
