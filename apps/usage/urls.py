from django.urls import path

from .views import usage_overview

app_name = "usage"
urlpatterns = [path("", usage_overview, name="overview")]
