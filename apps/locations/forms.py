from django import forms

from apps.projects.models import Project

from .models import Location


class LocationForm(forms.ModelForm):
    project = forms.ModelChoiceField(queryset=Project.objects.none(), required=False, label="Apply to all keywords in project", help_text="Optional. Existing and future keywords in this project will track this location.")

    class Meta:
        model = Location
        fields = ("country", "region", "city", "custom_name", "language_code", "latitude", "longitude")

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.projects.services import owned_projects

        self.fields["country"].queryset = self.fields["country"].queryset.filter(is_active=True)
        self.fields["project"].queryset = owned_projects(actor) if actor and actor.is_authenticated else Project.objects.none()
