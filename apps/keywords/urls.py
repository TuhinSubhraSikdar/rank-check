from django.urls import path

from . import views

app_name = "keywords"
urlpatterns = [
    path("sample.csv", views.keyword_sample, name="sample"),
    path("projects/<int:project_id>/", views.keyword_list, name="list"),
    path("projects/<int:project_id>/new/", views.keyword_create, name="create"),
    path("projects/<int:project_id>/import/", views.keyword_import, name="import"),
    path("projects/<int:project_id>/export/", views.keyword_export, name="export"),
    path("projects/<int:project_id>/<int:pk>/edit/", views.keyword_edit, name="edit"),
    path("projects/<int:project_id>/<int:pk>/archive/", views.keyword_archive, name="archive"),
]
