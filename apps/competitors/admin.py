from django.contrib import admin

from .models import Competitor, CompetitorResult

admin.site.register(Competitor)
admin.site.register(CompetitorResult)
