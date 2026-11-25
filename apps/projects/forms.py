from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django import forms

from .models import Project


class ProjectForm(forms.ModelForm):
    website_url = forms.URLField(max_length=500, assume_scheme="https")

    class Meta:
        model = Project
        fields = ("name", "website_url", "root_domain", "description", "country_code", "default_language", "default_device", "default_location", "match_subdomains", "time_zone")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.locations.services import owned_locations

        self.fields["default_location"].queryset = owned_locations(actor) if actor and actor.is_authenticated else self.fields["default_location"].queryset.none()
        self.fields["default_location"].label = "Track all keywords in this location"
        self.fields["default_location"].help_text = "Existing and newly added keywords will be assigned to this location. Per-keyword locations remain available."

    def clean_time_zone(self):
        value = self.cleaned_data["time_zone"].strip()
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise forms.ValidationError("Enter a valid IANA time zone, such as Asia/Kolkata.") from exc
        return value
