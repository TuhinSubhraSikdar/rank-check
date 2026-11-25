from django.contrib import admin

from .models import KeywordLocation, RankCheck, RankingResult

admin.site.register(KeywordLocation)
admin.site.register(RankCheck)
admin.site.register(RankingResult)
