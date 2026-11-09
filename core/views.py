import re
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import HelpRequestForm
from .models import Incident, Request


def home(request):
    active_incidents = Incident.objects.filter(status="Active")
    return render(request, "core/home.html", {"active_incidents": active_incidents})


def request_help(request):
    if request.method == "POST":
        form = HelpRequestForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            # If exactly one incident is active, attach the request to it automatically.
            active = Incident.objects.filter(status="Active")
            if active.count() == 1:
                obj.incident = active.first()
            obj.save()
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


# ---------- Organization side ----------

def is_org_user(user):
    """Superusers, and users in the 'Organization' group, may use the dashboard."""
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name="Organization").exists()
    )


org_required = user_passes_test(is_org_user, login_url="login")


@org_required
def dashboard(request):
    status = request.GET.get("status", "")
    incident_id = request.GET.get("incident", "")

    qs = Request.objects.select_related("incident").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    if incident_id.isdigit():
        qs = qs.filter(incident_id=int(incident_id))

    # Flag requests that have been Pending for more than 24 hours.
    cutoff = timezone.now() - timedelta(hours=24)
    rows = list(qs)
    for r in rows:
        r.attention = r.status == "Pending" and r.created_at < cutoff

    counts = [
        (label, Request.objects.filter(status=value).count())
        for value, label in Request.STATUS_CHOICES
    ]

    return render(request, "core/dashboard.html", {
        "rows": rows,
        "counts": counts,
        "statuses": Request.STATUS_CHOICES,
        "priorities": Request.PRIORITY_CHOICES,
        "incidents": Incident.objects.all(),
        "status": status,
        "selected_incident": incident_id,
    })


@org_required
@require_POST
def update_request(request, pk):
    obj = get_object_or_404(Request, pk=pk)
    new_status = request.POST.get("status")
    new_priority = request.POST.get("priority")

    if new_status in {value for value, _ in Request.STATUS_CHOICES}:
        obj.status = new_status
    if new_priority in {value for value, _ in Request.PRIORITY_CHOICES}:
        obj.priority = new_priority
    obj.save()

    messages.success(request, f"{obj.reference_code} updated: {obj.status}, {obj.priority} priority.")
    return redirect(f"{reverse('dashboard')}?{request.POST.get('qs', '')}")
