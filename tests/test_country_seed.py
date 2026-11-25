import pytest
from django.core.management import call_command

from apps.locations.models import Country

pytestmark = pytest.mark.django_db


def test_country_seed_is_repeatable_and_keeps_existing_edits():
    call_command("seed_countries")
    assert Country.objects.filter(iso_code="IN", name="India", is_active=True).exists()
    assert Country.objects.filter(iso_code="US", name="United States").exists()
    count = Country.objects.count()
    india = Country.objects.get(iso_code="IN")
    india.name = "India (custom)"
    india.save()
    call_command("seed_countries")
    assert Country.objects.count() == count
    assert Country.objects.get(iso_code="IN").name == "India (custom)"
