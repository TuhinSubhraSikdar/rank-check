from django.urls import path

from . import views

app_name = "competitors"
urlpatterns = [
    path("projects/<int:project_id>/", views.competitor_list, name="list"),
    path("projects/<int:project_id>/new/", views.competitor_create, name="create"),
    path("projects/<int:project_id>/<int:pk>/archive/", views.competitor_archive, name="archive"),
]
