from django.urls import path

from . import views

app_name = "reports"
urlpatterns = [
    path("", views.report_list, name="list"),
    path("projects/<int:project_id>/generate/", views.generate, name="generate"),
    path("<uuid:report_id>/", views.preview, name="preview"),
    path("<uuid:report_id>/<str:format>/", views.download, name="download"),
]
