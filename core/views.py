import re
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import HelpRequestForm, OfferForm
from .models import Incident, Request, RequestItem, ResourceOffer, Shelter
from .services import StockError, available_offers, sync_reservations

# Item categories and the older "need type" categories on a request.
CATEGORY_TO_NEED = {
    "water": "food_water",
    "food": "food_water",
    "shelter": "shelter",
    "medical": "medical",
    "clothing_hygiene": "clothing",
    "transport": "transport",
    "other": "other",
}


def _single_active_incident():
    """The active incident, if exactly one is active. Otherwise None."""
    active = Incident.objects.filter(status="Active")
    return active.first() if active.count() == 1 else None


def _group_offers(offers):
    """Group offers by item category, as a list of (category name, [offers])."""
    groups = {}
    for offer in offers:
        groups.setdefault(offer.item.get_category_display(), []).append(offer)
    return list(groups.items())


def home(request):
    active_incidents = Incident.objects.filter(status="Active")
    return render(request, "core/home.html", {"active_incidents": active_incidents})


# ---------- Public side ----------

def _parse_item_lines(post, offers):
    """Read the qty_<offer id> boxes. Returns (lines, error message)."""
    lines = []
    for offer in offers:
        raw = post.get(f"qty_{offer.pk}", "").strip()
        if not raw:
            continue
        try:
            qty = int(raw)
        except ValueError:
            return [], f"Enter a whole number for {offer.item.name}."
        if qty <= 0:
            continue
        if qty > offer.quantity_available:
            return [], f"Only {offer.quantity_available} {offer.item.unit} of {offer.item.name} is available."
        lines.append((offer, qty))
    return lines, ""


def request_help(request):
    offers = list(available_offers())
    item_error = ""
    other_need = ""
    chosen = {}

    if request.method == "POST":
        form = HelpRequestForm(request.POST)
        lines, item_error = _parse_item_lines(request.POST, offers)
        other_need = request.POST.get("other_need", "").strip()
        if not item_error and not lines and not other_need:
            item_error = "Choose at least one item, or describe what you need."

        if form.is_valid() and not item_error:
            with transaction.atomic():
                obj = form.save(commit=False)
                obj.incident = _single_active_incident()
                first_category = lines[0][0].item.category if lines else "other"
                obj.need_type = CATEGORY_TO_NEED.get(first_category, "other")
                obj.other_need = other_need[:300]
                obj.save()
                for offer, qty in lines:
                    RequestItem.objects.create(
                        help_request=obj, offer=offer, item=offer.item, quantity=qty,
                    )
            return redirect("request_submitted", reference=obj.reference_code)

        chosen = {o.pk: request.POST.get(f"qty_{o.pk}", "") for o in offers}
    else:
        form = HelpRequestForm()
        preselect = request.GET.get("offer", "")
        if preselect.isdigit():
            chosen = {int(preselect): "1"}

    for offer in offers:
        offer.chosen = chosen.get(offer.pk, "")

    return render(request, "core/request_form.html", {
        "form": form,
        "offers_by_category": _group_offers(offers),
        "item_error": item_error,
        "other_need": other_need,
    })


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


def offer_resources(request):
    incident = _single_active_incident()

    if request.method == "POST":
        form = OfferForm(request.POST, incident=incident)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.incident = incident
            obj.status = "Pending"
            obj.valid_until = timezone.now() + timedelta(hours=int(form.cleaned_data["valid_hours"]))
            obj.save()
            return redirect("offer_thanks")
    else:
        form = OfferForm(incident=incident)

    return render(request, "core/offer_form.html", {"form": form, "incident": incident})


def offer_thanks(request):
    return render(request, "core/offer_thanks.html")


def find_help(request):
    shelters = list(Shelter.objects.all())
    for shelter in shelters:
        shelter.free = max(shelter.capacity - shelter.occupancy, 0)
    return render(request, "core/find_help.html", {
        "groups": _group_offers(list(available_offers())),
        "shelters": shelters,
    })


# ---------- Organization side ----------

def is_org_user(user):
    """Superusers, and users in the 'Organization' group, may use the dashboard."""
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name="Organization").exists()
    )


org_required = user_passes_test(is_org_user, login_url="login")


def _pending_offers():
    return ResourceOffer.objects.filter(status="Pending").count()


@org_required
def dashboard(request):
    status = request.GET.get("status", "")
    incident_id = request.GET.get("incident", "")

    qs = (
        Request.objects.select_related("incident")
        .prefetch_related("lines__item")
        .order_by("-created_at")
    )
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
        "pending_offers": _pending_offers(),
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

    try:
        # If the stock cannot be reserved, the whole change is undone.
        with transaction.atomic():
            obj.save()
            sync_reservations(obj)
    except StockError as exc:
        messages.error(request, f"{obj.reference_code} was not changed. {exc}")
    else:
        messages.success(request, f"{obj.reference_code} updated: {obj.status}, {obj.priority} priority.")

    return redirect(f"{reverse('dashboard')}?{request.POST.get('qs', '')}")


@org_required
def dashboard_offers(request):
    now = timezone.now()
    offers = list(ResourceOffer.objects.select_related("item", "incident").order_by("-created_at"))
    for o in offers:
        o.expired = o.valid_until <= now
    return render(request, "core/offers.html", {
        "offers": offers,
        "statuses": ResourceOffer.STATUS_CHOICES,
        "pending_offers": _pending_offers(),
    })


@org_required
@require_POST
def update_offer(request, pk):
    offer = get_object_or_404(ResourceOffer, pk=pk)
    new_status = request.POST.get("status")

    if new_status in {value for value, _ in ResourceOffer.STATUS_CHOICES}:
        offer.status = new_status
        # Activating an offer that has already run out of time renews it for 72 hours.
        if new_status == "Active" and offer.valid_until <= timezone.now():
            offer.valid_until = timezone.now() + timedelta(hours=72)
        offer.save()
        messages.success(request, f"Offer updated: {offer.item.name} is now {offer.get_status_display()}.")

    return redirect("dashboard_offers")
