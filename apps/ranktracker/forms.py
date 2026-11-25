from django import forms

from apps.locations.services import owned_locations

from .models import KeywordLocation


class KeywordLocationForm(forms.ModelForm):
    class Meta:
        model = KeywordLocation
        fields = ("location", "device", "requested_depth")

    def __init__(self, *args, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["location"].queryset = owned_locations(actor)
        self.fields["device"].choices = [("DEFAULT", "Provider default")]
        self.fields["requested_depth"].choices = [(10, "Top 10")]
        self.fields["device"].help_text = "Device-specific Serper results are pending provider verification."
