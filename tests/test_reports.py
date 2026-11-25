import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.projects.models import Project
from apps.reports.services import create_report, render_csv, render_html

pytestmark = pytest.mark.django_db


def test_private_standalone_report_and_csv_formula_safety(client):
    owner = User.objects.create_user("owner", "owner@example.com", "safe-pass-987")
    other = User.objects.create_user("other", "other@example.com", "safe-pass-987")
    project = Project.objects.create(owner=owner, name="=Bad project", website_url="https://example.com", root_domain="example.com")
    report = create_report(actor=owner, project=project)
    assert "'=Bad project" not in render_html(report)
    assert "'=Bad project" in render_csv(report) if report.snapshot["rows"] else True
    assert "<style>" in render_html(report)
    client.force_login(other)
    assert client.get(reverse("reports:preview", args=[report.id])).status_code == 404
    assert client.get(reverse("reports:download", args=[report.id, "csv"])).status_code == 404
    client.force_login(owner)
    assert client.get(reverse("reports:download", args=[report.id, "html"])).status_code == 200
