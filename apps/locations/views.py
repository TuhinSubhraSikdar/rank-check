from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import LocationForm
from .services import archive_location, owned_locations, save_location


@login_required
def location_list(request):
    return render(request, "locations/list.html", {"title": "Locations", "locations": owned_locations(request.user)})


@login_required
def location_create(request):
    form = LocationForm(request.POST or None, actor=request.user)
    if request.method == "POST" and form.is_valid():
        save_location(actor=request.user, form=form)
        messages.success(request, "Location created.")
        return redirect("locations:list")
    return render(request, "locations/form.html", {"title": "New location", "form": form})


@login_required
def location_edit(request, pk):
    location = get_object_or_404(owned_locations(request.user), pk=pk)
    form = LocationForm(request.POST or None, instance=location, actor=request.user)
    if request.method == "POST" and form.is_valid():
        save_location(actor=request.user, form=form)
        messages.success(request, "Location updated.")
        return redirect("locations:list")
    return render(request, "locations/form.html", {"title": "Edit location", "form": form})


@login_required
def location_archive(request, pk):
    location = get_object_or_404(owned_locations(request.user), pk=pk)
    if request.method == "POST":
        archive_location(actor=request.user, location_id=location.id)
        messages.success(request, "Location archived.")
    return redirect("locations:list")
