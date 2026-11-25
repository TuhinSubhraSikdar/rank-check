import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.urls import reverse

from apps.accounts.models import User
from apps.keywords.models import Keyword
from apps.keywords.services import import_keywords
from apps.locations.models import Country, Location
from apps.projects.models import Project, normalize_domain
from apps.ranktracker.models import KeywordLocation

pytestmark = pytest.mark.django_db


@pytest.fixture
def users():
    return (
        User.objects.create_user("alice", "alice@example.com", "strong-password-534"),
        User.objects.create_user("bob", "bob@example.com", "strong-password-534"),
    )


@pytest.fixture
def project(users):
    return Project.objects.create(owner=users[0], name="Acme", website_url="HTTPS://WWW.Example.COM/", root_domain="www.example.com", time_zone="Asia/Kolkata")


def test_domain_normalization_and_boundaries(project):
    assert project.root_domain == "example.com"
    assert project.website_url == "https://example.com"
    assert normalize_domain("https://shop.Example.com/path") == "shop.example.com"
    with pytest.raises(ValidationError):
        normalize_domain("localhost")


def test_project_crud_is_tenant_isolated(client, users, project):
    alice, bob = users
    client.force_login(alice)
    assert client.get(reverse("projects:detail", args=[project.id])).status_code == 200
    client.force_login(bob)
    assert client.get(reverse("projects:detail", args=[project.id])).status_code == 404
    assert client.post(reverse("projects:archive", args=[project.id])).status_code == 404
    project.refresh_from_db()
    assert project.is_active


def test_project_create_and_archive_preserves_record(client, users):
    client.force_login(users[0])
    response = client.post(reverse("projects:create"), {"name": "Site", "website_url": "https://www.example.org/", "root_domain": "", "description": "", "country_code": "in", "default_language": "EN", "default_device": "DEFAULT", "time_zone": "Asia/Kolkata"})
    assert response.status_code == 302
    project = Project.objects.get(name="Site")
    assert (project.root_domain, project.country_code, project.default_language) == ("example.org", "IN", "en")
    assert client.post(reverse("projects:archive", args=[project.id])).status_code == 302
    project.refresh_from_db()
    assert not project.is_active


def test_keyword_crud_cannot_cross_projects(client, users, project):
    other = Project.objects.create(owner=users[1], name="Other", website_url="https://other.example", root_domain="other.example")
    keyword = Keyword.objects.create(project=project, text=" SEO   Agency ")
    assert keyword.text == "SEO Agency"
    client.force_login(users[1])
    assert client.get(reverse("keywords:edit", args=[other.id, keyword.id])).status_code == 404
    assert client.post(reverse("keywords:archive", args=[other.id, keyword.id])).status_code == 404
    keyword.refresh_from_db()
    assert keyword.is_active


def test_csv_import_is_atomic_and_skips_duplicates(users, project):
    Keyword.objects.create(project=project, text="existing")
    upload = SimpleUploadedFile("keywords.csv", b"keyword,target_url,tags,search_intent\nnew term,https://example.com/new,one,commercial\nNew  Term,,,\nexisting,,,\n,,,\n")
    result = import_keywords(actor=users[0], project_id=project.id, upload=upload)
    assert (result.created, result.skipped) == (1, 3)
    assert Keyword.objects.get(text="new term").search_intent == "COMMERCIAL"
    invalid = SimpleUploadedFile("bad.csv", b"keyword,target_url\ngood,\nbad,not-a-url\n")
    with pytest.raises(ValidationError):
        import_keywords(actor=users[0], project_id=project.id, upload=invalid)
    assert not Keyword.objects.filter(text="good").exists()


def test_csv_import_requires_header_and_export_neutralizes_formula(client, users, project):
    with pytest.raises(ValidationError):
        import_keywords(actor=users[0], project_id=project.id, upload=SimpleUploadedFile("bad.csv", b"phrase\nhello\n"))
    Keyword.objects.create(project=project, text="=HYPERLINK(1)")
    client.force_login(users[0])
    response = client.get(reverse("keywords:export", args=[project.id]))
    assert response.status_code == 200
    assert "'=HYPERLINK(1)" in response.content.decode("utf-8-sig")


def test_location_and_tracking_configuration_enforce_owner(users, project):
    country = Country.objects.create(name="India", iso_code="IN", google_country_code="in")
    location = Location.objects.create(owner=users[0], country=country, city="Kolkata", language_code="en")
    keyword = Keyword.objects.create(project=project, text="seo company")
    config = KeywordLocation.objects.create(keyword=keyword, location=location)
    assert config.requested_depth == 10
    foreign = Location.objects.create(owner=users[1], country=country, city="Mumbai", language_code="en")
    with pytest.raises(ValidationError):
        KeywordLocation.objects.create(keyword=keyword, location=foreign)
    with pytest.raises((IntegrityError, ValidationError)):
        KeywordLocation.objects.create(keyword=keyword, location=location)


def test_location_views_are_tenant_isolated(client, users):
    country = Country.objects.create(name="United Kingdom", iso_code="GB", google_country_code="gb")
    location = Location.objects.create(owner=users[0], country=country, city="London")
    client.force_login(users[1])
    assert client.get(reverse("locations:edit", args=[location.id])).status_code == 404
    assert client.post(reverse("locations:archive", args=[location.id])).status_code == 404
