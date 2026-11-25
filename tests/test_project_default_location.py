import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import User
from apps.keywords.forms import KeywordForm
from apps.keywords.models import Keyword
from apps.keywords.services import import_keywords, save_keyword
from apps.locations.models import Country, Location
from apps.projects.models import Project
from apps.projects.services import save_project
from apps.ranktracker.models import KeywordLocation

pytestmark = pytest.mark.django_db


def project_data(location_id):
    return {
        "name": "Site", "website_url": "https://example.com", "root_domain": "example.com",
        "description": "", "country_code": "IN", "default_language": "en",
        "default_device": "DEFAULT", "default_location": location_id,
        "match_subdomains": "on", "time_zone": "Asia/Kolkata",
    }


def test_project_location_assigns_existing_new_and_imported_keywords(client):
    owner = User.objects.create_user("owner", "owner@example.com", "safe-pass-534")
    country = Country.objects.create(name="India", iso_code="IN", google_country_code="in")
    location = Location.objects.create(owner=owner, country=country, city="Kolkata")
    project = Project.objects.create(owner=owner, name="Site", website_url="https://example.com", root_domain="example.com")
    existing = Keyword.objects.create(project=project, text="existing")
    saved, form = save_project(actor=owner, data=project_data(location.id), instance=project)
    assert saved is not None, form.errors
    assert KeywordLocation.objects.filter(keyword=existing, location=location).exists()
    form = KeywordForm({"text": "new manual", "target_url": "", "tags": "", "search_intent": ""})
    assert form.is_valid()
    new = save_keyword(actor=owner, project=project, form=form)
    assert KeywordLocation.objects.filter(keyword=new, location=location).exists()
    upload = SimpleUploadedFile("keywords.csv", b"keyword\nnew imported\n")
    import_keywords(actor=owner, project_id=project.id, upload=upload)
    assert KeywordLocation.objects.filter(keyword__text="new imported", location=location).exists()
    save_project(actor=owner, data=project_data(location.id), instance=project)
    assert KeywordLocation.objects.filter(keyword=existing, location=location).count() == 1


def test_project_location_cannot_cross_users(client):
    owner = User.objects.create_user("owner", "owner@example.com", "safe-pass-534")
    other = User.objects.create_user("other", "other@example.com", "safe-pass-534")
    country = Country.objects.create(name="India", iso_code="IN", google_country_code="in")
    foreign = Location.objects.create(owner=other, country=country, city="Mumbai")
    project = Project.objects.create(owner=owner, name="Site", website_url="https://example.com", root_domain="example.com")
    client.force_login(owner)
    response = client.post(reverse("projects:edit", args=[project.id]), project_data(foreign.id))
    assert response.status_code == 200
    project.refresh_from_db()
    assert project.default_location_id is None


def test_location_form_applies_to_project_keywords(client):
    owner = User.objects.create_user("owner", "owner@example.com", "safe-pass-534")
    country = Country.objects.create(name="India", iso_code="IN", google_country_code="in")
    project = Project.objects.create(owner=owner, name="Site", website_url="https://example.com", root_domain="example.com")
    keyword = Keyword.objects.create(project=project, text="seo")
    client.force_login(owner)
    response = client.post(reverse("locations:create"), {
        "country": country.id, "region": "", "city": "Kolkata", "custom_name": "",
        "language_code": "en", "latitude": "", "longitude": "", "project": project.id,
    })
    assert response.status_code == 302
    project.refresh_from_db()
    assert project.default_location.city == "Kolkata"
    assert KeywordLocation.objects.filter(keyword=keyword, location=project.default_location).exists()


def test_switching_project_location_archives_only_automatic_assignments():
    owner = User.objects.create_user("owner", "owner@example.com", "safe-pass-534")
    country = Country.objects.create(name="India", iso_code="IN", google_country_code="in")
    first = Location.objects.create(owner=owner, country=country, city="Kolkata")
    second = Location.objects.create(owner=owner, country=country, city="Mumbai")
    manual = Location.objects.create(owner=owner, country=country, city="Delhi")
    project = Project.objects.create(owner=owner, name="Site", website_url="https://example.com", root_domain="example.com")
    keyword = Keyword.objects.create(project=project, text="seo")
    manual_config = KeywordLocation.objects.create(keyword=keyword, location=manual)
    save_project(actor=owner, data=project_data(first.id), instance=project)
    first_config = KeywordLocation.objects.get(keyword=keyword, location=first)
    assert first_config.source == "PROJECT"
    save_project(actor=owner, data=project_data(second.id), instance=project)
    first_config.refresh_from_db()
    manual_config.refresh_from_db()
    assert not first_config.is_active
    assert manual_config.is_active
    assert KeywordLocation.objects.get(keyword=keyword, location=second).is_active
