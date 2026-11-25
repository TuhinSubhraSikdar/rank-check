from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import ProfileForm
from .models import Profile


@login_required
def settings_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your settings have been saved.")
        return redirect("settings")
    return render(request, "accounts/settings.html", {"form": form, "title": "Account settings"})
