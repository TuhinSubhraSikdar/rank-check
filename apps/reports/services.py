import csv
import io
import re

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from apps.dashboard.services import latest_results
from apps.keywords.services import safe_csv_cell

from .models import Report


@transaction.atomic
def create_report(*, actor, project, title=None):
    if project.owner_id != actor.id:
        raise PermissionDenied
    rows = []
    for result in latest_results(actor):
        config = result.rank_check.configuration
        if config.keyword.project_id != project.id:
            continue
        rows.append({
            "keyword": config.keyword.text,
            "target_url": config.keyword.target_url,
            "country": config.location.country.name,
            "region": config.location.region,
            "city": config.location.city,
            "location": config.location.display_name,
            "language": config.location.language_code,
            "device": config.device,
            "position": result.position,
            "previous_position": result.previous_position,
            "movement": result.movement,
            "ranking_url": result.ranking_url,
            "depth": result.rank_check.actual_checked_depth,
            "status": result.status,
            "provider": result.rank_check.provider,
            "checked_at": result.checked_at.isoformat(),
        })
    ranked = [row for row in rows if row["position"] is not None]
    summary = {
        "total": len(rows),
        "top3": sum(row["position"] <= 3 for row in ranked),
        "top10": sum(row["position"] <= 10 for row in ranked),
        "improved": sum(row["movement"] is not None and row["movement"] > 0 for row in ranked),
        "declined": sum(row["movement"] is not None and row["movement"] < 0 for row in ranked),
        "unchanged": sum(row["movement"] == 0 for row in ranked),
        "not_found": sum(row["status"] == "NOT_FOUND" for row in rows),
    }
    locations = {}
    for row in rows:
        item = locations.setdefault(row["location"], {"name": row["location"], "tracked": 0, "top10": 0, "not_found": 0})
        item["tracked"] += 1
        item["top10"] += bool(row["position"] is not None and row["position"] <= 10)
        item["not_found"] += row["status"] == "NOT_FOUND"
    profile = getattr(actor, "profile", None)
    snapshot = {
        "project_name": project.name,
        "website": project.website_url,
        "generated_at": timezone.now().isoformat(),
        "company_name": profile.company_name if profile else "",
        "contact": profile.contact_information if profile else "",
        "brand_color": profile.brand_color if profile and re.fullmatch(r"#[0-9A-Fa-f]{6}", profile.brand_color) else "#2563EB",
        "summary": summary,
        "locations": list(locations.values()),
        "rows": rows,
    }
    return Report.objects.create(owner=actor, project=project, title=title or f"{project.name} ranking report", snapshot=snapshot)


def render_html(report):
    return render_to_string("reports/standalone.html", {"report": report, "data": report.snapshot})


def render_csv(report):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(("Project Name", "Website", "Keyword", "Target URL", "Country", "State", "City", "Language", "Device", "Current Position", "Previous Position", "Position Change", "Ranking URL", "Checked Depth", "Check Status", "Provider", "Check Date"))
    for row in report.snapshot["rows"]:
        writer.writerow([safe_csv_cell(value) for value in (report.snapshot["project_name"], report.snapshot["website"], row["keyword"], row["target_url"], row["country"], row["region"], row["city"], row["language"], row["device"], row["position"], row["previous_position"], row["movement"], row["ranking_url"], row["depth"], row["status"], row["provider"], row["checked_at"])])
    return "\ufeff" + output.getvalue()
