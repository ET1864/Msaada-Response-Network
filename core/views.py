import re

from django.shortcuts import get_object_or_404, redirect, render

from .forms import HelpRequestForm
from .models import Request


def home(request):
    return render(request, "core/home.html")


def request_help(request):
    if request.method == "POST":
        form = HelpRequestForm(request.POST)
        if form.is_valid():
            obj = form.save()
            return redirect("request_submitted", reference=obj.reference_code)
    else:
        form = HelpRequestForm()
    return render(request, "core/request_form.html", {"form": form})


def request_submitted(request, reference):
    obj = get_object_or_404(Request, reference_code=reference)
    return render(request, "core/request_submitted.html", {"req": obj})


def _last9(phone):
    """Compare phone numbers by their last 9 digits, so 0712 345 678 matches +254712345678."""
    return re.sub(r"\D", "", phone or "")[-9:]


def track_request(request):
    ref = request.GET.get("ref", "").strip().upper()
    phone = request.GET.get("phone", "").strip()
    result = None
    not_found = False

    if ref and phone:
        obj = Request.objects.filter(reference_code=ref).first()
        if obj and _last9(phone) and _last9(obj.phone) == _last9(phone):
            result = obj
        else:
            not_found = True

    return render(request, "core/track.html", {
        "ref": ref, "phone": phone, "result": result, "not_found": not_found,
    })
