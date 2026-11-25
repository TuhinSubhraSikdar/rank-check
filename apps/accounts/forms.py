from django import forms
from django.core.validators import RegexValidator

from .models import Profile


class ProfileForm(forms.ModelForm):
    brand_color = forms.CharField(validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$")])

    class Meta:
        model = Profile
        fields = ("company_name", "contact_information", "brand_color", "theme")
