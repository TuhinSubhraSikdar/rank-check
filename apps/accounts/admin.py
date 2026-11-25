from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Profile, User


@admin.register(User)
class RankTrackerUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Usage", {"fields": ("monthly_request_quota",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Account", {"fields": ("email",)}),)


admin.site.register(Profile)
