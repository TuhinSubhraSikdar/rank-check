from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import JsonResponse
from django.urls import include, path

from apps.accounts import views as accounts
from apps.dashboard.views import overview

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", lambda request: JsonResponse({"status": "ok"}), name="health"),
    path("", overview, name="dashboard"),
    path("accounts/settings/", accounts.settings_view, name="settings"),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("projects/", include("apps.projects.urls")),
    path("keywords/", include("apps.keywords.urls")),
    path("locations/", include("apps.locations.urls")),
    path("tracking/", include("apps.ranktracker.urls")),
    path("reports/", include("apps.reports.urls")),
    path("competitors/", include("apps.competitors.urls")),
    path("schedules/", include("apps.scheduling.urls")),
    path("usage/", include("apps.usage.urls")),
]
