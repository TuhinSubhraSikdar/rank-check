from django import forms

from .models import Keyword


class KeywordForm(forms.ModelForm):
    target_url = forms.URLField(max_length=500, required=False, assume_scheme="https")

    class Meta:
        model = Keyword
        fields = ("text", "target_url", "tags", "search_intent")


class KeywordCSVForm(forms.Form):
    file = forms.FileField(help_text="UTF-8 CSV, maximum 2 MB and 5,000 data rows.")

    def clean_file(self):
        upload = self.cleaned_data["file"]
        if upload.size > 2 * 1024 * 1024:
            raise forms.ValidationError("CSV file exceeds the 2 MB limit.")
        if not upload.name.lower().endswith(".csv"):
            raise forms.ValidationError("Upload a .csv file.")
        return upload
