import csv
import io
from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from apps.projects.models import Project

from .models import Keyword


@dataclass(frozen=True)
class ImportResult:
    created: int
    skipped: int


def owned_keywords(actor, *, project=None, include_archived=False):
    queryset = Keyword.objects.filter(project__owner=actor).select_related("project")
    if project is not None:
        if project.owner_id != actor.id:
            raise PermissionDenied
        queryset = queryset.filter(project=project)
    return queryset if include_archived else queryset.filter(is_active=True, project__is_active=True)


@transaction.atomic
def save_keyword(*, actor, project, form):
    if project.owner_id != actor.id or not project.is_active:
        raise PermissionDenied
    keyword = form.save(commit=False)
    if keyword.pk and keyword.project_id != project.id:
        raise PermissionDenied
    keyword.project = project
    keyword.save()
    from apps.ranktracker.services import ensure_project_default_configurations

    ensure_project_default_configurations(project=project, keywords=[keyword])
    return keyword


@transaction.atomic
def archive_keyword(*, actor, keyword_id):
    keyword = owned_keywords(actor).select_for_update().get(pk=keyword_id)
    keyword.is_active = False
    keyword.save(update_fields=("is_active", "updated_at"))
    return keyword


def _decode_upload(upload):
    raw = upload.read()
    if b"\x00" in raw:
        raise ValidationError("CSV contains invalid null bytes.")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError("CSV must use UTF-8 encoding.") from exc


@transaction.atomic
def import_keywords(*, actor, project_id, upload):
    project = Project.objects.filter(owner=actor, is_active=True).get(pk=project_id)
    reader = csv.DictReader(io.StringIO(_decode_upload(upload)))
    headers = {str(name).strip().lower() for name in (reader.fieldnames or [])}
    if "keyword" not in headers:
        raise ValidationError("CSV requires a keyword column.")
    rows, seen, skipped = [], set(), 0
    existing = {text.casefold() for text in project.keywords.values_list("text", flat=True)}
    for number, source in enumerate(reader, start=2):
        if number > 5001:
            raise ValidationError("CSV exceeds the 5,000 row limit.")
        row = {str(key).strip().lower(): (value or "").strip() for key, value in source.items() if key}
        text = " ".join(row.get("keyword", "").split())
        if not text:
            skipped += 1
            continue
        key = text.casefold()
        if key in seen or key in existing:
            skipped += 1
            continue
        seen.add(key)
        keyword = Keyword(project=project, text=text, target_url=row.get("target_url", ""), tags=row.get("tags", ""), search_intent=row.get("search_intent", "").upper())
        keyword.full_clean()
        rows.append(keyword)
    try:
        Keyword.objects.bulk_create(rows)
        from apps.ranktracker.services import ensure_project_default_configurations

        ensure_project_default_configurations(project=project, keywords=rows)
    except IntegrityError as exc:
        raise ValidationError("Keywords changed during import; retry with a fresh export.") from exc
    return ImportResult(created=len(rows), skipped=skipped)


def safe_csv_cell(value):
    text = "" if value is None else str(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text
