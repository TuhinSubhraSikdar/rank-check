import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.projects.models import Project
from apps.scheduling.models import TrackingSchedule

pytestmark = pytest.mark.django_db


def test_schedule_owner_and_calendar_month(client):
    owner = User.objects.create_user("owner", "owner@example.com", "safe-pass-987")
    outsider = User.objects.create_user("other", "other@example.com", "safe-pass-987")
    project = Project.objects.create(owner=owner, name="Site", website_url="https://example.com", root_domain="example.com", time_zone="Asia/Kolkata")
    client.force_login(outsider)
    assert client.post(reverse("scheduling:edit", args=[project.id]), {"frequency": "MONTHLY", "is_active": "on"}).status_code == 404
    client.force_login(owner)
    response = client.post(reverse("scheduling:edit", args=[project.id]), {"frequency": "MONTHLY", "is_active": "on"})
    assert response.status_code == 302
    schedule = TrackingSchedule.objects.get(project=project)
    assert schedule.is_active
    assert schedule.next_run_at.tzinfo is not None
