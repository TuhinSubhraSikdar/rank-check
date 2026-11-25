from django.urls import path

from . import views

app_name = "scheduling"
urlpatterns = [
    path("", views.schedule_list, name="list"),
    path("projects/<int:project_id>/", views.schedule_edit, name="edit"),
]
