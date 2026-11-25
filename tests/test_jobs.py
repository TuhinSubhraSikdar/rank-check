from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.keywords.models import Keyword
from apps.locations.models import Country, Location
from apps.projects.models import Project
from apps.ranktracker.models import KeywordLocation, RankCheck
from apps.scheduling.services import cancel_job, queue_job

pytestmark = pytest.mark.django_db


def test_job_confirmation_ownership_quota_and_cancel(client):
    owner = User.objects.create_user("owner", "owner@example.com", "safe-pass-987", monthly_request_quota=2)
    outsider = User.objects.create_user("other", "other@example.com", "safe-pass-987")
    project = Project.objects.create(owner=owner, name="Site", website_url="https://example.com", root_domain="example.com")
    country = Country.objects.create(name="India", iso_code="IN", google_country_code="in")
    location = Location.objects.create(owner=owner, country=country, city="Kolkata")
    for text in ("seo one", "seo two"):
        keyword = Keyword.objects.create(project=project, text=text)
        KeywordLocation.objects.create(keyword=keyword, location=location)
    client.force_login(outsider)
    assert client.get(reverse("ranktracker:run", args=[project.id])).status_code == 404
    client.force_login(owner)
    assert client.get(reverse("ranktracker:run", args=[project.id])).status_code == 200
    assert client.get(reverse("ranktracker:history"), {"status": "PENDING"}).status_code == 200
    response = client.post(reverse("ranktracker:run", args=[project.id]))
    assert response.status_code == 302
    assert RankCheck.objects.filter(job__project=project).count() == 2
    with pytest.raises(ValidationError):
        queue_job(actor=owner, project=project)
    job = RankCheck.objects.first().job
    cancel_job(actor=owner, job_id=job.id)
    assert not RankCheck.objects.filter(job=job, status="PENDING").exists()


@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
def test_job_confirmation_keeps_checks_pending_when_broker_unavailable(client):
    owner = User.objects.create_user("owner", "owner@example.com", "safe-pass-987")
    project = Project.objects.create(
        owner=owner, name="Site", website_url="https://example.com", root_domain="example.com"
    )
    country = Country.objects.create(name="India", iso_code="IN", google_country_code="in")
    location = Location.objects.create(owner=owner, country=country, city="Kolkata")
    keyword = Keyword.objects.create(project=project, text="seo")
    KeywordLocation.objects.create(keyword=keyword, location=location)
    client.force_login(owner)
    with patch("apps.ranktracker.views.dispatch_pending.delay", side_effect=ConnectionError):
        response = client.post(reverse("ranktracker:run", args=[project.id]), follow=True)
    assert response.status_code == 200
    assert b"task broker is unavailable" in response.content
    assert RankCheck.objects.get(job__project=project).status == "PENDING"
