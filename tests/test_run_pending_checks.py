from unittest.mock import patch

import pytest
from django.core.management import call_command

from apps.accounts.models import User
from apps.keywords.models import Keyword
from apps.locations.models import Country, Location
from apps.projects.models import Project
from apps.ranktracker.models import KeywordLocation, RankCheck
from apps.scheduling.models import RankJob

pytestmark = pytest.mark.django_db


def test_command_only_claims_confirmed_pending_checks(settings):
    settings.SERPER_API_KEY = "test-placeholder"
    owner = User.objects.create_user("owner", "owner@example.com", "safe-pass-987")
    project = Project.objects.create(owner=owner, name="Site", website_url="https://example.com", root_domain="example.com")
    country = Country.objects.create(name="India", iso_code="IN", google_country_code="in")
    location = Location.objects.create(owner=owner, country=country, city="Kolkata")
    configuration = KeywordLocation.objects.create(keyword=Keyword.objects.create(project=project, text="seo"), location=location)
    job = RankJob.objects.create(owner=owner, project=project, total=1)
    check = RankCheck.objects.create(job=job, configuration=configuration, requested_depth=10)
    with patch("apps.scheduling.management.commands.run_pending_checks.run_check") as runner:
        call_command("run_pending_checks", "--project", str(project.id))
    check.refresh_from_db()
    assert check.status == "QUEUED"
    runner.assert_called_once_with(check.id)
