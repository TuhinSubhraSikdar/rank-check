from django.contrib.admin.apps import AdminConfig


class SuperuserAdminConfig(AdminConfig):
    default_site = "apps.core.admin_site.SuperuserAdminSite"
