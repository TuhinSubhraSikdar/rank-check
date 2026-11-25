from django import forms

from .models import TrackingSchedule


class TrackingScheduleForm(forms.ModelForm):
    class Meta:
        model = TrackingSchedule
        fields = ("frequency", "is_active")
