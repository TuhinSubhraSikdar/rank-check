from django.urls import path

from . import views

app_name = "ranktracker"
urlpatterns = [
    path("configurations/", views.configuration_list, name="configurations"),
    path("keywords/<int:keyword_id>/configure/", views.configuration_create, name="configure"),
    path("projects/<int:project_id>/run/", views.job_preview, name="run"),
    path("jobs/<int:job_id>/", views.job_detail, name="job"),
    path("jobs/<int:job_id>/cancel/", views.job_cancel, name="cancel"),
    path("history/", views.history, name="history"),
]
