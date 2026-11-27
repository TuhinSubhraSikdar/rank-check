from django.urls import path

from . import views

app_name = "ranktracker"
urlpatterns = [
    path("indexing/", views.index_batches, name="index_batches"),
    path("indexing/quick/", views.quick_index_create, name="index_quick"),
    path("indexing/new/", views.index_batch_create, name="index_new"),
    path("indexing/<int:batch_id>/", views.index_batch_detail, name="index_batch"),
    path("configurations/", views.configuration_list, name="configurations"),
    path("keywords/<int:keyword_id>/configure/", views.configuration_create, name="configure"),
    path("projects/<int:project_id>/run/", views.job_preview, name="run"),
    path("jobs/<int:job_id>/", views.job_detail, name="job"),
    path("jobs/<int:job_id>/cancel/", views.job_cancel, name="cancel"),
    path("history/", views.history, name="history"),
]
