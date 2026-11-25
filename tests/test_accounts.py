import pytest
from django.core import mail
from django.core.cache import cache
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def reset_cache():
    cache.clear()


def test_admin_created_user_login_logout(client):
    user = User.objects.create_user("alice", "ALICE@example.com", "Correct-Horse-Battery-97")
    assert user.email == "alice@example.com"
    assert client.get("/accounts/register/").status_code == 404
    assert client.post("/accounts/register/", {"username": "intruder"}).status_code == 404
    assert client.login(username="alice", password="Correct-Horse-Battery-97")
    assert client.get(reverse("dashboard")).status_code == 200
    assert client.get(reverse("logout")).status_code == 405
    assert client.post(reverse("logout")).status_code == 302
    assert client.get(reverse("dashboard")).status_code == 302
    assert client.login(username="alice", password="Correct-Horse-Battery-97")


def test_admin_only_superuser(client):
    staff = User.objects.create_user("staff", "staff@example.com", "safe-pass-534", is_staff=True)
    superuser = User.objects.create_superuser("root", "root@example.com", "safe-pass-534")
    client.force_login(staff)
    assert client.get(reverse("admin:index")).status_code != 200
    client.force_login(superuser)
    assert client.get(reverse("admin:index")).status_code == 200
    assert b'name="email"' in client.get(reverse("admin:accounts_user_add")).content


def test_reset_email_and_settings(client):
    user = User.objects.create_user("alice", "a@example.com", "a-strong-password-534")
    assert client.post(reverse("password_reset"), {"email": user.email}).status_code == 302
    assert len(mail.outbox) == 1
    client.force_login(user)
    response = client.post(reverse("settings"), {"company_name": "Agency", "contact_information": "contact@example.com", "brand_color": "#2563EB", "theme": "DARK"})
    assert response.status_code == 302
    assert user.profile.company_name == "Agency"
    assert user.profile.theme == "DARK"
    assert b'data-theme="dark"' in client.get(reverse("dashboard")).content


def test_auth_rate_limit(client):
    for _ in range(20):
        client.post(reverse("login"), {"username": "bad", "password": "bad"})
    assert client.post(reverse("login")).status_code == 429
